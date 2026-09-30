import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from openai import AsyncOpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Anomaly, Invoice
from app.schemas.anomaly import AnomalyAnalysisResponse, AnomalyDetectionResponse


@dataclass(frozen=True)
class InvoiceSnapshot:
    id: UUID
    supplier_id: UUID
    cost_center_id: UUID | None
    invoice_number: str
    issue_date: date
    amount: Decimal
    status: str = "pending"


@dataclass(frozen=True)
class DetectedAnomaly:
    related_invoice_id: UUID
    anomaly_type: str
    severity: str
    explanation: str
    metrics: dict[str, object]


def percentage_change(current: Decimal, baseline: Decimal) -> Decimal:
    if baseline == 0:
        return Decimal("0")
    return ((current - baseline) / baseline * Decimal("100")).quantize(Decimal("0.1"))


def detect_invoice_anomalies(invoices: list[InvoiceSnapshot]) -> list[DetectedAnomaly]:
    active = sorted(
        (invoice for invoice in invoices if invoice.status != "rejected"),
        key=lambda invoice: (invoice.issue_date, str(invoice.id)),
    )
    detected: list[DetectedAnomaly] = []
    supplier_history: dict[UUID, list[InvoiceSnapshot]] = defaultdict(list)
    seen_numbers: dict[str, list[InvoiceSnapshot]] = defaultdict(list)

    for invoice in active:
        history = [
            item
            for item in supplier_history[invoice.supplier_id]
            if item.issue_date >= invoice.issue_date - timedelta(days=183)
        ]
        if len(history) >= 3:
            average = sum((item.amount for item in history), Decimal("0")) / len(history)
            change = percentage_change(invoice.amount, average)
            if change >= Decimal("80"):
                severity = "high" if change >= Decimal("120") else "medium"
                detected.append(
                    DetectedAnomaly(
                        related_invoice_id=invoice.id,
                        anomaly_type="supplier_amount_spike",
                        severity=severity,
                        explanation=(
                            f"O valor da fatura está {change}% acima da média histórica "
                            f"do fornecedor nos últimos seis meses."
                        ),
                        metrics={
                            "current_amount": float(invoice.amount),
                            "historical_average": float(average.quantize(Decimal("0.01"))),
                            "percentage_change": float(change),
                            "history_count": len(history),
                            "window_days": 183,
                        },
                    )
                )

        normalized_number = invoice.invoice_number.strip().casefold()
        number_matches = [
            item
            for item in seen_numbers[normalized_number]
            if item.supplier_id != invoice.supplier_id
        ]
        if number_matches:
            detected.append(
                DetectedAnomaly(
                    related_invoice_id=invoice.id,
                    anomaly_type="duplicate_document_number",
                    severity="high",
                    explanation="O número do documento já foi utilizado por outro fornecedor.",
                    metrics={
                        "invoice_number": invoice.invoice_number,
                        "matching_invoice_ids": [str(item.id) for item in number_matches[:5]],
                    },
                )
            )

        close_matches = [
            item
            for item in history
            if item.amount == invoice.amount
            and abs((invoice.issue_date - item.issue_date).days) <= 7
        ]
        if close_matches:
            detected.append(
                DetectedAnomaly(
                    related_invoice_id=invoice.id,
                    anomaly_type="possible_duplicate_payment",
                    severity="high",
                    explanation=(
                        "Outra fatura do mesmo fornecedor e valor foi emitida em um intervalo "
                        "de até sete dias."
                    ),
                    metrics={
                        "amount": float(invoice.amount),
                        "days_apart": min(
                            abs((invoice.issue_date - item.issue_date).days)
                            for item in close_matches
                        ),
                        "matching_invoice_ids": [str(item.id) for item in close_matches[:5]],
                    },
                )
            )

        supplier_history[invoice.supplier_id].append(invoice)
        seen_numbers[normalized_number].append(invoice)

    detected.extend(detect_cost_center_growth(active))
    return detected


def detect_cost_center_growth(invoices: list[InvoiceSnapshot]) -> list[DetectedAnomaly]:
    by_center_month: dict[UUID, dict[tuple[int, int], list[InvoiceSnapshot]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for invoice in invoices:
        if invoice.cost_center_id:
            by_center_month[invoice.cost_center_id][
                (invoice.issue_date.year, invoice.issue_date.month)
            ].append(invoice)

    detected: list[DetectedAnomaly] = []
    for cost_center_id, months in by_center_month.items():
        ordered_months = sorted(months)
        if len(ordered_months) < 4:
            continue
        current_month = ordered_months[-1]
        previous_months = ordered_months[-4:-1]
        current_total = sum(
            (invoice.amount for invoice in months[current_month]), Decimal("0")
        )
        previous_totals = [
            sum((invoice.amount for invoice in months[month]), Decimal("0"))
            for month in previous_months
        ]
        average = sum(previous_totals, Decimal("0")) / len(previous_totals)
        change = percentage_change(current_total, average)
        if change < Decimal("50"):
            continue
        related = max(months[current_month], key=lambda invoice: invoice.issue_date)
        detected.append(
            DetectedAnomaly(
                related_invoice_id=related.id,
                anomaly_type="cost_center_monthly_growth",
                severity="high" if change >= Decimal("100") else "medium",
                explanation=(
                    f"O gasto mensal do centro de custo está {change}% acima da média "
                    "dos três meses anteriores."
                ),
                metrics={
                    "cost_center_id": str(cost_center_id),
                    "current_month": f"{current_month[0]:04d}-{current_month[1]:02d}",
                    "current_total": float(current_total),
                    "previous_three_month_average": float(
                        average.quantize(Decimal("0.01"))
                    ),
                    "percentage_change": float(change),
                },
            )
        )
    return detected


async def scan_company_anomalies(
    session: AsyncSession, company_id: UUID
) -> AnomalyDetectionResponse:
    invoice_rows = await session.scalars(
        select(Invoice).where(Invoice.company_id == company_id).order_by(Invoice.issue_date)
    )
    snapshots = [
        InvoiceSnapshot(
            id=invoice.id,
            supplier_id=invoice.supplier_id,
            cost_center_id=invoice.cost_center_id,
            invoice_number=invoice.invoice_number,
            issue_date=invoice.issue_date,
            amount=invoice.amount,
            status=invoice.status,
        )
        for invoice in invoice_rows
    ]
    findings = detect_invoice_anomalies(snapshots)
    existing = {
        (anomaly.related_invoice_id, anomaly.anomaly_type): anomaly
        for anomaly in await session.scalars(
            select(Anomaly).where(Anomaly.company_id == company_id)
        )
    }
    now = datetime.now(UTC)
    created = 0
    updated = 0
    for finding in findings:
        key = (finding.related_invoice_id, finding.anomaly_type)
        anomaly = existing.get(key)
        if anomaly:
            anomaly.severity = finding.severity
            anomaly.explanation = finding.explanation
            anomaly.metrics = finding.metrics
            updated += 1
        else:
            session.add(
                Anomaly(
                    company_id=company_id,
                    related_invoice_id=finding.related_invoice_id,
                    anomaly_type=finding.anomaly_type,
                    severity=finding.severity,
                    explanation=finding.explanation,
                    metrics=finding.metrics,
                    detected_at=now,
                )
            )
            created += 1
    await session.commit()
    return AnomalyDetectionResponse(detected=len(findings), created=created, updated=updated)


def demo_executive_analysis(anomaly: Anomaly, invoice: Invoice, supplier_name: str) -> str:
    severity = {"high": "alto", "medium": "moderado", "low": "baixo"}[anomaly.severity]
    return (
        f"Risco {severity}: a fatura {invoice.invoice_number}, de {supplier_name}, foi sinalizada "
        f"pela regra {anomaly.anomaly_type}. {anomaly.explanation} Recomenda-se validar o "
        "documento de origem, a aprovação e o histórico antes do pagamento."
    )


async def analyze_anomaly(
    session: AsyncSession, anomaly: Anomaly, invoice: Invoice, supplier_name: str
) -> AnomalyAnalysisResponse:
    if settings.ai_provider == "demo":
        analysis = demo_executive_analysis(anomaly, invoice, supplier_name)
        provider = "demo"
        model = "deterministic-executive-summary"
    else:
        if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
            raise RuntimeError("OPENAI_API_KEY is not configured")
        input_data = {
            "anomaly_type": anomaly.anomaly_type,
            "severity": anomaly.severity,
            "explanation": anomaly.explanation,
            "metrics": anomaly.metrics,
            "invoice_number": invoice.invoice_number,
            "supplier": supplier_name,
            "amount": float(invoice.amount),
            "issue_date": invoice.issue_date.isoformat(),
        }
        try:
            response = await AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value()
            ).responses.create(
                model=settings.openai_model,
                instructions=(
                    "Você é um analista financeiro. Produza uma explicação executiva curta em "
                    "português do Brasil usando somente os dados fornecidos. Não recalcule nem "
                    "invente métricas. Explique o risco e recomende verificações humanas, sem "
                    "autorizar ou bloquear pagamentos."
                ),
                input=json.dumps(input_data, ensure_ascii=False),
                store=False,
            )
        except OpenAIError as exc:
            raise RuntimeError("The anomaly analysis service is unavailable") from exc
        analysis = response.output_text
        provider = "openai"
        model = settings.openai_model
    analyzed_at = datetime.now(UTC)
    anomaly.ai_analysis = analysis
    anomaly.ai_provider = provider
    anomaly.ai_model = model
    anomaly.analyzed_at = analyzed_at
    anomaly.status = "reviewed"
    await session.commit()
    return AnomalyAnalysisResponse(
        anomaly_id=anomaly.id,
        analysis=analysis,
        provider=provider,
        model=model,
        analyzed_at=analyzed_at,
    )
