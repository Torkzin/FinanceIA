from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.anomalies import InvoiceSnapshot, detect_invoice_anomalies


def snapshot(
    *,
    supplier_id=None,
    cost_center_id=None,
    invoice_number="INV-1",
    issue_date=date(2026, 1, 1),
    amount="100.00",
) -> InvoiceSnapshot:
    return InvoiceSnapshot(
        id=uuid4(),
        supplier_id=supplier_id or uuid4(),
        cost_center_id=cost_center_id,
        invoice_number=invoice_number,
        issue_date=issue_date,
        amount=Decimal(amount),
    )


def test_detects_supplier_amount_spike_with_explainable_metrics() -> None:
    supplier_id = uuid4()
    invoices = [
        snapshot(
            supplier_id=supplier_id,
            invoice_number=f"BASE-{index}",
            issue_date=date(2026, 1, 1) + timedelta(days=index * 30),
            amount="100.00",
        )
        for index in range(3)
    ]
    outlier = snapshot(
        supplier_id=supplier_id,
        invoice_number="OUTLIER",
        issue_date=date(2026, 4, 15),
        amount="250.00",
    )

    findings = detect_invoice_anomalies([*invoices, outlier])
    spike = next(item for item in findings if item.anomaly_type == "supplier_amount_spike")

    assert spike.related_invoice_id == outlier.id
    assert spike.severity == "high"
    assert spike.metrics["historical_average"] == 100.0
    assert spike.metrics["percentage_change"] == 150.0


def test_detects_close_same_value_payment() -> None:
    supplier_id = uuid4()
    first = snapshot(
        supplier_id=supplier_id,
        invoice_number="A",
        issue_date=date(2026, 5, 1),
        amount="900.00",
    )
    second = snapshot(
        supplier_id=supplier_id,
        invoice_number="B",
        issue_date=date(2026, 5, 4),
        amount="900.00",
    )

    findings = detect_invoice_anomalies([first, second])

    assert any(
        item.anomaly_type == "possible_duplicate_payment"
        and item.related_invoice_id == second.id
        for item in findings
    )


def test_detects_document_number_reused_by_another_supplier() -> None:
    first = snapshot(invoice_number="NF-42")
    second = snapshot(invoice_number=" nf-42 ", issue_date=date(2026, 1, 2))

    findings = detect_invoice_anomalies([first, second])

    assert any(item.anomaly_type == "duplicate_document_number" for item in findings)


def test_detects_cost_center_monthly_growth() -> None:
    center_id = uuid4()
    invoices = [
        snapshot(
            cost_center_id=center_id,
            invoice_number=f"MONTH-{month}",
            issue_date=date(2026, month, 10),
            amount="100.00" if month < 4 else "220.00",
        )
        for month in range(1, 5)
    ]

    findings = detect_invoice_anomalies(invoices)
    growth = next(item for item in findings if item.anomaly_type == "cost_center_monthly_growth")

    assert growth.severity == "high"
    assert growth.metrics["percentage_change"] == 120.0
