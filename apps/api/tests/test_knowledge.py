import math

from app.services.knowledge import chunk_pages, demo_embedding


def test_chunk_pages_preserves_page_and_overlap() -> None:
    text = " ".join(f"palavra-{index}" for index in range(120))

    chunks = chunk_pages([(7, text)], maximum=180, overlap=30)

    assert len(chunks) > 1
    assert all(chunk.page_number == 7 for chunk in chunks)
    assert all(len(chunk.content) <= 180 for chunk in chunks)


def test_demo_embedding_is_deterministic_and_normalized() -> None:
    first = demo_embedding("Política de reembolso para hospedagem", dimensions=64)
    second = demo_embedding("Política de reembolso para hospedagem", dimensions=64)

    assert first == second
    assert len(first) == 64
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_demo_embedding_keeps_related_text_closer() -> None:
    query = demo_embedding("limite reembolso hospedagem", dimensions=256)
    related = demo_embedding("limite para reembolso de hospedagem", dimensions=256)
    unrelated = demo_embedding("cadastro de fornecedores internacionais", dimensions=256)

    related_score = sum(left * right for left, right in zip(query, related, strict=True))
    unrelated_score = sum(left * right for left, right in zip(query, unrelated, strict=True))

    assert related_score > unrelated_score
