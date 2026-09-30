from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.extraction import ConfirmDocumentExtraction
from app.services.ai_extraction import DemoDocumentExtractor


@pytest.mark.asyncio
async def test_demo_extractor_returns_validated_financial_fields(tmp_path) -> None:
    document = tmp_path / "invoice.pdf"
    document.write_bytes(
        b"%PDF-1.4\nFornecedor: Acme Cloud\nCNPJ: 12.345.678/0001-90\n"
        b"Fatura: INV-42\nValor: R$ 1.234,56\nEmissao: 2026-09-01\n"
        b"Vencimento: 2026-09-30\nDescricao: Cloud mensal\nCategoria: Tecnologia\n"
        b"Centro de custo: Tecnologia\n%%EOF"
    )

    result = await DemoDocumentExtractor().extract(document, "application/pdf")

    assert result.supplier_name == "Acme Cloud"
    assert result.invoice_number == "INV-42"
    assert result.amount == 1234.56
    assert result.issue_date == date(2026, 9, 1)
    assert result.confidence == 0.75


def test_confirmation_rejects_due_date_before_issue_date() -> None:
    with pytest.raises(ValidationError):
        ConfirmDocumentExtraction(
            supplier_id="00000000-0000-0000-0000-000000000001",
            invoice_number="INV-42",
            description="Cloud mensal",
            category="Tecnologia",
            issue_date=date(2026, 9, 30),
            due_date=date(2026, 9, 1),
            amount=Decimal("100.00"),
            currency="brl",
        )
