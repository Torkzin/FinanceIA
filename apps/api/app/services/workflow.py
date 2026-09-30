import unicodedata
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Anomaly
from app.schemas.workflow import WorkflowQueryResponse, WorkflowRoute
from app.services.financial_assistant import ask_financial_assistant
from app.services.knowledge import answer_knowledge_question


class WorkflowState(TypedDict, total=False):
    message: str
    session: AsyncSession
    company_id: UUID
    route: WorkflowRoute
    answer: str
    sources: list[dict[str, Any]]
    metadata: dict[str, Any]
    trace: list[str]
    validated: bool


def normalize(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(char) != "Mn"
    )


def route_intent(message: str) -> WorkflowRoute:
    text = normalize(message)
    if any(
        term in text
        for term in (
            "anomalia",
            "anomalias",
            "suspeit",
            "irregular",
            "fora do padrao",
            "desvio",
            "risco financeiro",
        )
    ):
        return "anomalies"
    if any(
        term in text
        for term in (
            "politica",
            "reembolso",
            "procedimento",
            "manual interno",
            "regra de compra",
            "permitido pela empresa",
            "limite de hospedagem",
        )
    ):
        return "knowledge"
    if any(
        term in text
        for term in (
            "extrair documento",
            "extracao de documento",
            "nota fiscal enviada",
            "processar pdf",
            "processar imagem",
        )
    ):
        return "documents"
    return "finance"


async def router_node(state: WorkflowState) -> dict[str, Any]:
    return {"route": route_intent(state["message"]), "trace": ["intent_router"]}


def choose_route(state: WorkflowState) -> WorkflowRoute:
    return state["route"]


async def finance_node(state: WorkflowState) -> dict[str, Any]:
    response = await ask_financial_assistant(
        state["message"], state["session"], state["company_id"]
    )
    return {
        "answer": response.answer,
        "sources": [],
        "metadata": {
            "provider": response.provider,
            "model": response.model,
            "tool": response.tool,
            "data": response.data,
        },
        "trace": [*state["trace"], "finance_tool_agent"],
    }


async def knowledge_node(state: WorkflowState) -> dict[str, Any]:
    response = await answer_knowledge_question(
        state["message"], 5, state["session"], state["company_id"]
    )
    return {
        "answer": response.answer,
        "sources": [source.model_dump(mode="json") for source in response.sources],
        "metadata": {
            "provider": response.provider,
            "model": response.model,
            "grounded": response.grounded,
        },
        "trace": [*state["trace"], "rag_agent"],
    }


async def anomaly_node(state: WorkflowState) -> dict[str, Any]:
    rows = (
        await state["session"].execute(
            select(Anomaly.anomaly_type, Anomaly.severity, func.count(Anomaly.id))
            .where(
                Anomaly.company_id == state["company_id"],
                Anomaly.status != "dismissed",
            )
            .group_by(Anomaly.anomaly_type, Anomaly.severity)
            .order_by(func.count(Anomaly.id).desc())
        )
    ).all()
    total = sum(row[2] for row in rows)
    if not rows:
        answer = (
            "Nenhuma anomalia ativa foi registrada. Um usuário administrador ou financeiro "
            "pode executar uma nova detecção na área de Anomalias."
        )
    else:
        type_labels = {
            "supplier_amount_spike": "valor acima do histórico",
            "duplicate_document_number": "número de documento repetido",
            "possible_duplicate_payment": "possível pagamento duplicado",
            "cost_center_monthly_growth": "crescimento do centro de custo",
        }
        severity_labels = {"high": "alta", "medium": "média", "low": "baixa"}
        details = ", ".join(
            f"{count} de {type_labels.get(anomaly_type, anomaly_type)} "
            f"(severidade {severity_labels.get(severity, severity)})"
            for anomaly_type, severity, count in rows
        )
        answer = f"Existem {total} anomalia(s) ativa(s): {details}."
    return {
        "answer": answer,
        "sources": [],
        "metadata": {
            "provider": "database",
            "model": "deterministic-anomaly-summary",
            "total": total,
            "groups": [
                {"anomaly_type": row[0], "severity": row[1], "count": row[2]}
                for row in rows
            ],
        },
        "trace": [*state["trace"], "anomaly_agent"],
    }


async def document_node(state: WorkflowState) -> dict[str, Any]:
    return {
        "answer": (
            "O processamento de documentos exige um arquivo e revisão humana. Acesse a área "
            "Documentos, envie um PDF ou imagem, execute a extração e confirme os campos antes "
            "de criar a fatura."
        ),
        "sources": [],
        "metadata": {
            "provider": "workflow",
            "model": "document-safety-guidance",
            "requires_upload": True,
            "requires_human_review": True,
        },
        "trace": [*state["trace"], "document_agent"],
    }


async def validation_node(state: WorkflowState) -> dict[str, Any]:
    answer = state.get("answer", "").strip()
    metadata = state.get("metadata", {})
    valid = bool(answer)
    if state["route"] == "finance":
        valid = valid and bool(metadata.get("tool"))
    elif state["route"] == "knowledge":
        grounded = metadata.get("grounded") is True
        safely_abstained = metadata.get("grounded") is False and not state.get("sources")
        valid = valid and ((grounded and bool(state.get("sources"))) or safely_abstained)
    elif state["route"] == "documents":
        valid = valid and metadata.get("requires_human_review") is True
    elif state["route"] == "anomalies":
        valid = valid and isinstance(metadata.get("total"), int)
    if not valid:
        answer = (
            "Não foi possível validar a resposta com as proteções exigidas. "
            "Tente reformular a pergunta."
        )
    return {
        "answer": answer,
        "validated": valid,
        "trace": [*state["trace"], "response_validator"],
    }


def build_workflow():
    builder = StateGraph(WorkflowState)
    builder.add_node("router", router_node)
    builder.add_node("finance", finance_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("anomalies", anomaly_node)
    builder.add_node("documents", document_node)
    builder.add_node("validate", validation_node)
    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        choose_route,
        {
            "finance": "finance",
            "knowledge": "knowledge",
            "anomalies": "anomalies",
            "documents": "documents",
        },
    )
    for node in ("finance", "knowledge", "anomalies", "documents"):
        builder.add_edge(node, "validate")
    builder.add_edge("validate", END)
    return builder.compile()


workflow = build_workflow()


async def run_workflow(
    message: str, session: AsyncSession, company_id: UUID
) -> WorkflowQueryResponse:
    result = await workflow.ainvoke(
        {"message": message, "session": session, "company_id": company_id}
    )
    return WorkflowQueryResponse(
        answer=result["answer"],
        route=result["route"],
        trace=result["trace"],
        sources=result.get("sources", []),
        metadata=result.get("metadata", {}),
        validated=result["validated"],
    )
