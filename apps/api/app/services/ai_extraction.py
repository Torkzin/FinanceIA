import base64
import logging
import re
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings
from app.schemas.extraction import ExtractedInvoiceData

logger = logging.getLogger("finance_ai.ai")

EXTRACTION_INSTRUCTIONS = """
Extract financial invoice data from the supplied document. Do not guess values that are not
visible; use null and add a short warning instead. Normalize currency to an ISO 4217 code and
dates to ISO format. Confidence is an overall 0-to-1 assessment. Business validation and record
creation happen separately after human review.
""".strip()


class ExtractionUnavailableError(RuntimeError):
    pass


class DocumentExtractor(Protocol):
    provider: str
    model: str

    async def extract(self, path: Path, media_type: str) -> ExtractedInvoiceData: ...


class OpenAIDocumentExtractor:
    provider = "openai"

    def __init__(self) -> None:
        if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
            raise ExtractionUnavailableError("OPENAI_API_KEY is not configured")
        self.model = settings.openai_model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def extract(self, path: Path, media_type: str) -> ExtractedInvoiceData:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        if media_type == "application/pdf":
            content = [
                {
                    "type": "input_file",
                    "filename": path.name,
                    "file_data": f"data:{media_type};base64,{encoded}",
                },
                {"type": "input_text", "text": "Extract the financial fields for review."},
            ]
        else:
            content = [
                {
                    "type": "input_image",
                    "image_url": f"data:{media_type};base64,{encoded}",
                    "detail": "high",
                },
                {"type": "input_text", "text": "Extract the financial fields for review."},
            ]

        started = perf_counter()
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=EXTRACTION_INSTRUCTIONS,
                input=[{"role": "user", "content": content}],
                text_format=ExtractedInvoiceData,
                store=False,
            )
        except OpenAIError as exc:
            logger.warning(
                "ai_extraction_failed",
                extra={
                    "model": self.model,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )
            raise ExtractionUnavailableError("The AI extraction service is unavailable") from exc

        result = response.output_parsed
        if result is None:
            raise ExtractionUnavailableError("The AI did not return extractable financial data")
        usage = response.usage
        logger.info(
            "ai_extraction_completed",
            extra={
                "model": self.model,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
        )
        return result


class DemoDocumentExtractor:
    provider = "demo"
    model = "deterministic-fixture-parser"

    async def extract(self, path: Path, media_type: str) -> ExtractedInvoiceData:
        text = path.read_bytes().decode("latin-1", errors="ignore")

        def match(label: str) -> str | None:
            found = re.search(rf"{label}\s*:\s*([^\r\n)]+)", text, re.IGNORECASE)
            return found.group(1).strip() if found else None

        def parsed_date(label: str) -> date | None:
            value = match(label)
            if not value:
                return None
            for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(value, pattern).replace(tzinfo=UTC).date()
                except ValueError:
                    continue
            return None

        amount_text = match("Valor")
        amount = None
        if amount_text:
            normalized = re.sub(r"[^0-9,.-]", "", amount_text).replace(".", "").replace(",", ".")
            try:
                amount = float(normalized)
            except ValueError:
                pass
        return ExtractedInvoiceData(
            document_type="invoice",
            supplier_name=match("Fornecedor"),
            supplier_document_number=match("CNPJ"),
            invoice_number=match("Fatura"),
            amount=amount,
            currency="BRL",
            issue_date=parsed_date("Emissao"),
            due_date=parsed_date("Vencimento"),
            description=match("Descricao"),
            category=match("Categoria"),
            cost_center_name=match("Centro de custo"),
            confidence=0.75,
            warnings=[
                "Demo provider used; configure AI_PROVIDER=openai for model-based extraction."
            ],
        )


def get_document_extractor() -> DocumentExtractor:
    if settings.ai_provider == "demo":
        return DemoDocumentExtractor()
    if settings.ai_provider != "openai":
        raise ExtractionUnavailableError(f"Unsupported AI provider: {settings.ai_provider}")
    return OpenAIDocumentExtractor()
