from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents: list[dict], chunk_size: int = 500, chunk_overlap: int = 80) -> list[dict]:
    """Split article documents while retaining article metadata on every chunk."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "다.", ". ", " ", ""],
    )
    chunks = []
    for doc in documents:
        for index, text in enumerate(splitter.split_text(doc["text"])):
            chunks.append({
                "id": f'{doc["article_id"]}-{index}',
                "text": text,
                "article_id": doc["article_id"],
                "title": doc["title"],
                "source": doc["source"],
            })
    return chunks
