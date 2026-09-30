import json
import re
import unicodedata
from datetime import date
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI, OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.assistant import FinancialChatResponse
from app.services import financial_tools

TOOLS = [
    {
        "type": "function",
        "name": "get_upcoming_payments",
        "description": "Get pending or approved payments due in the next number of days.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90}},
            "required": ["days"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_overdue_invoices",
        "description": "Get invoices that are currently overdue.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_expenses_by_period",
        "description": (
            "Calculate company expenses in a date period, optionally filtered by category."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "format": "date"},
                "date_to": {"type": "string", "format": "date"},
                "category": {"type": ["string", "null"]},
            },
            "required": ["date_from", "date_to", "category"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_top_suppliers",
        "description": "Rank suppliers by total invoice amount.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 10}},
            "required": ["limit"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_cost_center_summary",
        "description": "Summarize total expenses grouped by cost center.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "compare_monthly_expenses",
        "description": "Compare expenses in the current month with the previous month.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]

INSTRUCTIONS = """You are FinanceAI, a concise financial operations assistant. You must use one
of the supplied read-only tools for every financial answer. Never invent values and never request
or expose data outside the current company. Answer in Brazilian Portuguese, state the period used,
and format monetary values in BRL when the tool returns BRL-denominated data."""


def normalize(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(char) != "Mn"
    )


async def execute_tool(
    name: str, arguments: dict[str, Any], session: AsyncSession, company_id: UUID
) -> dict[str, Any]:
    if name == "get_upcoming_payments":
        return await financial_tools.get_upcoming_payments(
            session, company_id, int(arguments["days"])
        )
    if name == "get_overdue_invoices":
        return await financial_tools.get_overdue_invoices(session, company_id)
    if name == "get_expenses_by_period":
        return await financial_tools.get_expenses_by_period(
            session,
            company_id,
            date.fromisoformat(arguments["date_from"]),
            date.fromisoformat(arguments["date_to"]),
            arguments.get("category"),
        )
    if name == "get_top_suppliers":
        return await financial_tools.get_top_suppliers(session, company_id, int(arguments["limit"]))
    if name == "get_cost_center_summary":
        return await financial_tools.get_cost_center_summary(session, company_id)
    if name == "compare_monthly_expenses":
        return await financial_tools.compare_monthly_expenses(session, company_id)
    raise ValueError("Unsupported financial tool")


def brl(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def deterministic_answer(name: str, data: dict[str, Any]) -> str:
    if name == "get_upcoming_payments":
        return (
            f"Nos próximos {data['days']} dias há {data['count']} pagamento(s), "
            f"totalizando {brl(data['total'])}."
        )
    if name == "get_overdue_invoices":
        return f"Existem {data['count']} fatura(s) vencida(s), somando {brl(data['total'])}."
    if name == "get_expenses_by_period":
        category = f" em {data['category']}" if data["category"] else ""
        return (
            f"De {data['date_from']} a {data['date_to']}, foram {data['count']} "
            f"despesa(s){category}, no total de {brl(data['total'])}."
        )
    if name == "get_top_suppliers":
        names = ", ".join(f"{item['supplier']} ({brl(item['total'])})" for item in data["items"])
        return f"Os maiores fornecedores por valor são: {names}."
    if name == "get_cost_center_summary":
        if not data["items"]:
            return "Não há despesas associadas a centros de custo."
        leader = data["items"][0]
        return (
            f"O centro de custo com maior gasto é {leader['cost_center']}, "
            f"com {brl(leader['total'])}."
        )
    current, previous = data["current"], data["previous"]
    percentage = data["percentage_change"]
    change = "sem base de comparação" if percentage is None else f"variação de {percentage:+.1f}%"
    return (
        f"O mês atual soma {brl(current['total'])}; o anterior, "
        f"{brl(previous['total'])}. Resultado: {change}."
    )


def route_demo_question(message: str) -> tuple[str, dict[str, Any]]:
    text = normalize(message)
    if "vencid" in text or "atrasad" in text:
        return "get_overdue_invoices", {}
    if "maior" in text and "fornecedor" in text:
        match = re.search(r"\b(\d{1,2})\b", text)
        return "get_top_suppliers", {"limit": int(match.group(1)) if match else 5}
    if "centro de custo" in text:
        return "get_cost_center_summary", {}
    if "compar" in text or "mes anterior" in text:
        return "compare_monthly_expenses", {}
    if "venc" in text or "proxim" in text or "pagamento" in text:
        match = re.search(r"\b(\d{1,2})\b", text)
        return "get_upcoming_payments", {"days": int(match.group(1)) if match else 15}
    today = date.today()
    category = (
        "Tecnologia" if any(term in text for term in ("tecnologia", "cloud", "software")) else None
    )
    return "get_expenses_by_period", {
        "date_from": today.replace(day=1).isoformat(),
        "date_to": today.isoformat(),
        "category": category,
    }


async def ask_financial_assistant(
    message: str, session: AsyncSession, company_id: UUID
) -> FinancialChatResponse:
    if settings.ai_provider == "demo":
        name, arguments = route_demo_question(message)
        data = await execute_tool(name, arguments, session, company_id)
        return FinancialChatResponse(
            answer=deterministic_answer(name, data),
            tool=name,
            data=data,
            provider="demo",
            model="deterministic-intent-router",
        )
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    try:
        first = await client.responses.create(
            model=settings.openai_model,
            instructions=INSTRUCTIONS,
            input=message,
            tools=TOOLS,
            tool_choice="required",
            parallel_tool_calls=False,
            store=False,
        )
        call = next(item for item in first.output if item.type == "function_call")
        arguments = json.loads(call.arguments)
        data = await execute_tool(call.name, arguments, session, company_id)
        final = await client.responses.create(
            model=settings.openai_model,
            instructions=INSTRUCTIONS,
            previous_response_id=first.id,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(data),
                }
            ],
            tools=TOOLS,
            store=False,
        )
    except (OpenAIError, StopIteration, ValueError, KeyError) as exc:
        raise RuntimeError("The financial assistant is unavailable") from exc
    return FinancialChatResponse(
        answer=final.output_text,
        tool=call.name,
        data=data,
        provider="openai",
        model=settings.openai_model,
    )
