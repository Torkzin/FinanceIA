import pytest

from app.services.workflow import (
    build_workflow,
    document_node,
    route_intent,
    validation_node,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Quais pagamentos vencem nos próximos 15 dias?", "finance"),
        ("Qual é a política de reembolso?", "knowledge"),
        ("Existem despesas suspeitas ou anomalias?", "anomalies"),
        ("Quero extrair documento enviado", "documents"),
    ],
)
def test_routes_intent_to_small_specialized_workflows(message, expected) -> None:
    assert route_intent(message) == expected


def test_graph_contains_router_specialists_and_validator() -> None:
    nodes = build_workflow().get_graph().nodes

    assert {"router", "finance", "knowledge", "anomalies", "documents", "validate"} <= set(
        nodes
    )


@pytest.mark.asyncio
async def test_knowledge_validator_accepts_safe_abstention_without_sources() -> None:
    result = await validation_node(
        {
            "route": "knowledge",
            "answer": "Não encontrei uma fonte interna relevante.",
            "sources": [],
            "metadata": {"grounded": False},
            "trace": ["intent_router", "rag_agent"],
        }
    )

    assert result["validated"] is True
    assert result["trace"][-1] == "response_validator"


@pytest.mark.asyncio
async def test_knowledge_validator_blocks_ungrounded_answer() -> None:
    result = await validation_node(
        {
            "route": "knowledge",
            "answer": "O limite é R$ 999.",
            "sources": [],
            "metadata": {"grounded": True},
            "trace": ["intent_router", "rag_agent"],
        }
    )

    assert result["validated"] is False
    assert "Não foi possível validar" in result["answer"]


@pytest.mark.asyncio
async def test_document_agent_requires_upload_and_human_review() -> None:
    result = await document_node({"trace": ["intent_router"]})

    assert result["metadata"]["requires_upload"] is True
    assert result["metadata"]["requires_human_review"] is True
