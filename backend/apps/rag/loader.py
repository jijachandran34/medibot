import re
import logging
from pathlib import Path

from django.conf import settings
import chromadb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "medical_knowledge"


def _chroma_client():
    path = str(settings.BASE_DIR / "chroma_db")
    return chromadb.PersistentClient(path=path)


def _parse_chunks(text):
    """Split knowledge base text into one chunk per ENTRY block."""
    # Split on every line that begins with "ENTRY:" (keeps the ENTRY: header in each chunk)
    chunks = re.split(r'\n(?=ENTRY:)', text.strip())
    return [c.strip() for c in chunks if c.strip()]


def load_knowledge():
    """
    Load medical_knowledge.txt into ChromaDB.
    Idempotent — deletes and recreates the collection on each call.
    """
    knowledge_file = settings.BASE_DIR / "data" / "medical_knowledge.txt"
    if not knowledge_file.exists():
        logger.error("medical_knowledge.txt not found at %s", knowledge_file)
        return 0

    text = knowledge_file.read_text(encoding="utf-8")
    chunks = _parse_chunks(text)
    if not chunks:
        logger.warning("No chunks parsed from medical_knowledge.txt")
        return 0

    client = _chroma_client()

    # Delete existing collection so re-running is safe
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing '%s' collection.", COLLECTION_NAME)
    except Exception:
        pass  # Collection didn't exist — that's fine

    collection = client.create_collection(COLLECTION_NAME)
    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
    )

    logger.info("Loaded %d chunks into ChromaDB collection '%s'.", len(chunks), COLLECTION_NAME)
    print(f"RAG: loaded {len(chunks)} chunks into '{COLLECTION_NAME}'.")
    return len(chunks)
