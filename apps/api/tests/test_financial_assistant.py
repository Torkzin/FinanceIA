from app.services.financial_assistant import deterministic_answer, route_demo_question


def test_demo_router_selects_upcoming_payments_and_days() -> None:
    tool, arguments = route_demo_question("Quais pagamentos vencem nos próximos 20 dias?")

    assert tool == "get_upcoming_payments"
    assert arguments == {"days": 20}


def test_demo_router_selects_read_only_financial_tools() -> None:
    assert route_demo_question("Existem despesas vencidas?")[0] == "get_overdue_invoices"
    assert route_demo_question("Quais são nossos cinco maiores fornecedores?")[0] == (
        "get_top_suppliers"
    )
    assert route_demo_question("Qual centro de custo mais gastou?")[0] == (
        "get_cost_center_summary"
    )
    assert route_demo_question("Compare este mês com o mês anterior")[0] == (
        "compare_monthly_expenses"
    )


def test_deterministic_answer_formats_brl() -> None:
    answer = deterministic_answer(
        "get_overdue_invoices", {"count": 2, "total": 1234.56, "items": []}
    )

    assert "R$ 1.234,56" in answer
