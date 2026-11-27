def _cut_at_boundary(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return len(text)
    window = text[start:end]
    # Prefer natural Korean/legal text boundaries near the target size.
    for separator in ("\n\n", "\n", "다.", ". ", " "):
        position = window.rfind(separator)
        if position >= int(len(window) * 0.65):
            return start + position + len(separator)
    return end


def split_documents(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 80) -> list[dict]:
    """Split each article into overlapping character chunks and preserve citations."""
    if chunk_size <= 0:
        raise ValueError("chunk_size는 0보다 커야 합니다.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap은 0 이상 chunk_size 미만이어야 합니다.")

    chunks = []
    for doc in documents:
        text = " ".join(doc["text"].split())
        start = 0
        index = 0
        while start < len(text):
            end = _cut_at_boundary(text, start, min(start + chunk_size, len(text)))
            piece = text[start:end].strip()
            if piece:
                chunks.append({
                    "id": f'{doc["article_id"]}-{index}',
                    "text": piece,
                    "article_id": doc["article_id"],
                    "title": doc["title"],
                    "source": doc["source"],
                })
                index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - chunk_overlap)
    return chunks
