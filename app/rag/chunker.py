def _cut_at_boundary(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return len(text)
    window = text[start:end]
    for separator in ("。", ". ", "다.", "\n", " "):
        position = window.rfind(separator)
        if position >= int(len(window) * 0.65):
            return start + position + len(separator)
    return end


def split_documents(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 80) -> list[dict]:
    """리뷰 본문은 설정 길이로 나누고, 임베딩 입력에는 영화·리뷰 제목을 함께 넣는다."""
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
                embedding_text = f'영화: {doc["movie_title"]}\n리뷰 제목: {doc["title"]}\n{piece}'
                chunks.append({
                    "id": f'{doc["document_id"]}-{index}',
                    "document_id": doc["document_id"],
                    "review_id": doc["review_id"],
                    "movie_code": doc["movie_code"],
                    "movie_title": doc["movie_title"],
                    "text": piece,
                    "embedding_text": embedding_text,
                    "title": doc["title"],
                    "source": doc["source"],
                    "chunk_index": index,
                })
                index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - chunk_overlap)
    return chunks
