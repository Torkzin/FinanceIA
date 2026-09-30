import asyncio
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from openai import AsyncOpenAI, OpenAIError
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeQueryResponse, KnowledgeSource

MAX_CHUNK_CHARACTERS = 1100
CHUNK_OVERLAP = 180
MINIMUM_SIMILARITY = 0.25
STOP_WORDS = {
    "a",
    "as",
    "ao",
    "aos",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "entre",
    "essa",
    "esse",
    "esta",
    "este",
    "eu",
    "o",
    "os",
    "para",
    "por",
    "qual",
    "que",
    "se",
    "sem",
    "sobre",
    "um",
    "uma",
}


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None


class KnowledgeProcessingError(RuntimeError):
    pass


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _tokens(value: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{2,}", normalize_text(value))
    return [word for word in words if word not in STOP_WORDS]


def demo_embedding(value: str, dimensions: int | None = None) -> list[float]:
    size = dimensions or settings.embedding_dimensions
    vector = [0.0] * size
    tokens = _tokens(value)
    features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % size
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    magnitude = math.sqrt(sum(component * component for component in vector))
    return vector if magnitude == 0 else [component / magnitude for component in vector]


def chunk_pages(
    pages: list[tuple[int | None, str]],
    *,
    maximum: int = MAX_CHUNK_CHARACTERS,
    overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page_number, raw_text in pages:
        text = re.sub(r"\s+", " ", raw_text).strip()
        start = 0
        while start < len(text):
            end = min(start + maximum, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + maximum // 2, end)
                if boundary > start:
                    end = boundary
            content = text[start:end].strip()
            if content:
                chunks.append(TextChunk(content=content, page_number=page_number))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks


def _read_pages(path: Path, media_type: str) -> list[tuple[int | None, str]]:
    if media_type == "text/plain":
        return [(1, path.read_text(encoding="utf-8-sig"))]
    try:
        reader = PdfReader(path)
        return [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, 1)]
    except Exception as exc:
        raise KnowledgeProcessingError("Não foi possível ler o PDF enviado") from exc


class EmbeddingProvider:
    @property
    def provider(self) -> str:
        return "demo" if settings.ai_provider == "demo" else "openai"

    @property
    def model(self) -> str:
        return (
            "deterministic-feature-hash"
            if settings.ai_provider == "demo"
            else settings.openai_embedding_model
        )

    async def embed_many(self, values: list[str]) -> list[list[float]]:
        if settings.ai_provider == "demo":
            return [demo_embedding(value) for value in values]
        if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
            raise KnowledgeProcessingError("OPENAI_API_KEY is not configured")
        try:
            response = await AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value()
            ).embeddings.create(
                model=settings.openai_embedding_model,
                input=values,
                dimensions=settings.embedding_dimensions,
                encoding_format="float",
            )
        except OpenAIError as exc:
            raise KnowledgeProcessingError("O serviço de embeddings está indisponível") from exc
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


embedding_provider = EmbeddingProvider()


async def index_document(
    session: AsyncSession, document: KnowledgeDocument, path: Path
) -> KnowledgeDocument:
    pages = await asyncio.to_thread(_read_pages, path, document.media_type)
    chunks = chunk_pages(pages)
    if not chunks:
        raise KnowledgeProcessingError("O documento não contém texto pesquisável")
    embeddings = await embedding_provider.embed_many([chunk.content for chunk in chunks])
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        session.add(
            KnowledgeChunk(
                company_id=document.company_id,
                document_id=document.id,
                chunk_index=index,
                page_number=chunk.page_number,
                content=chunk.content,
                character_count=len(chunk.content),
                embedding=embedding,
            )
        )
    document.page_count = len(pages)
    document.chunk_count = len(chunks)
    document.embedding_provider = embedding_provider.provider
    document.embedding_model = embedding_provider.model
    document.status = "indexed"
    document.processing_error = None
    return document


async def answer_knowledge_question(
    question: str,
    limit: int,
    session: AsyncSession,
    company_id: UUID,
) -> KnowledgeQueryResponse:
    query_vector = (await embedding_provider.embed_many([question]))[0]
    distance = KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
    rows = (
        await session.execute(
            select(KnowledgeChunk, KnowledgeDocument, distance)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.company_id == company_id,
                KnowledgeDocument.company_id == company_id,
                KnowledgeDocument.status == "indexed",
            )
            .order_by(distance)
            .limit(limit)
        )
    ).all()
    sources = [
        KnowledgeSource(
            document_id=document.id,
            document_name=document.original_name,
            excerpt=chunk.content,
            page_number=chunk.page_number,
            similarity=round(max(0.0, min(1.0, 1.0 - float(row_distance))), 4),
        )
        for chunk, document, row_distance in rows
        if 1.0 - float(row_distance) >= MINIMUM_SIMILARITY
    ]
    if not sources:
        return KnowledgeQueryResponse(
            answer=(
                "Não encontrei uma fonte interna relevante para responder com segurança. "
                "Envie ou atualize o documento da política correspondente."
            ),
            sources=[],
            grounded=False,
            provider=embedding_provider.provider,
            model=embedding_provider.model,
        )
    if settings.ai_provider == "demo":
        lead = sources[0]
        page = f", página {lead.page_number}" if lead.page_number else ""
        answer = f"Segundo {lead.document_name}{page}: {lead.excerpt}"
        return KnowledgeQueryResponse(
            answer=answer,
            sources=sources,
            grounded=True,
            provider="demo",
            model="extractive-rag",
        )
    context = "\n\n".join(
        f"[Fonte {index}: {source.document_name}, página {source.page_number or 'N/A'}]\n"
        f"{source.excerpt}"
        for index, source in enumerate(sources, 1)
    )
    try:
        response = await AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()  # type: ignore[union-attr]
        ).responses.create(
            model=settings.openai_model,
            instructions=(
                "Responda em português do Brasil usando exclusivamente o contexto fornecido. "
                "Cite as fontes como [Fonte N]. Se o contexto não sustentar a resposta, diga que "
                "não há informação suficiente. Não invente regras, valores ou procedimentos."
            ),
            input=f"Contexto:\n{context}\n\nPergunta: {question}",
            store=False,
        )
    except OpenAIError as exc:
        raise KnowledgeProcessingError("O assistente de conhecimento está indisponível") from exc
    return KnowledgeQueryResponse(
        answer=response.output_text,
        sources=sources,
        grounded=True,
        provider="openai",
        model=settings.openai_model,
    )
