from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import EMBEDDING_MODEL, VECTORSTORE_DIR
from src.ingest import build_vectorstore

_vectorstore = None


def get_vectorstore():
    """Load the FAISS index once and reuse it. Build it first if it does not exist."""
    global _vectorstore
    if _vectorstore is None:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        if (Path(VECTORSTORE_DIR) / "index.faiss").exists():
            _vectorstore = FAISS.load_local(
                VECTORSTORE_DIR,
                embeddings,
                allow_dangerous_deserialization=True,  # safe here: we created this index ourselves
            )
        else:
            _vectorstore = build_vectorstore(embeddings)
    return _vectorstore


def retrieve(query: str, k: int = 4):
    """Return the top-k most relevant chunks for a query."""
    return get_vectorstore().similarity_search(query, k=k)


def retrieve_relevant(query: str, k: int = 5, margin: float = 0.3, min_keep: int = 2):
    """Retrieve top-k chunks, then drop the ones much less relevant than the best match.

    FAISS returns a distance (lower = more similar). We keep chunks whose distance
    is within `margin` of the best one, and always keep at least `min_keep`.
    """
    results = get_vectorstore().similarity_search_with_score(query, k=k)
    results.sort(key=lambda r: r[1])

    best_score = results[0][1]
    kept = [doc for doc, score in results if score <= best_score + margin]

    if len(kept) < min_keep:
        kept = [doc for doc, _ in results[:min_keep]]
    return kept


def format_context(docs) -> str:
    """Join retrieved chunks into one text block for the LLM prompt."""
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown").replace("\\", "/").split("/")[-1]
        parts.append(f"[Source: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)