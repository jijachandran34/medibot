import logging

from django.conf import settings
import chromadb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "medical_knowledge"


def _chroma_client():
    path = str(settings.BASE_DIR / "chroma_db")
    return chromadb.PersistentClient(path=path)


def query_rag(symptom_text, n_results=3):
    """
    Query the medical knowledge ChromaDB collection.
    Returns top n_results chunks joined into a single string.
    Returns empty string if collection is empty or any error occurs.
    """
    if not symptom_text or not symptom_text.strip():
        return ""

    try:
        client = _chroma_client()
        collection = client.get_collection(COLLECTION_NAME)

        # Guard: don't request more results than documents exist
        count = collection.count()
        if count == 0:
            return ""
        n = min(n_results, count)

        results = collection.query(
            query_texts=[symptom_text.strip()],
            n_results=n,
        )
        docs = results.get("documents", [[]])[0]
        return "\n\n---\n\n".join(docs) if docs else ""

    except Exception as exc:
        logger.warning("RAG query failed: %s", exc)
        return ""
