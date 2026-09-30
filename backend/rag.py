import chromadb
import httpx

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="knowledge_base")

async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        response = await http_client.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text}
        )
        return response.json()["embedding"]

async def add_document(doc_id: str, text: str, metadata: dict = None):
    embedding = await get_embedding(text)
    safe_metadata = metadata if metadata else {"source": "manual"}
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[safe_metadata]
    )

async def search_similar(query: str, n_results: int = 3) -> list[str]:
    if collection.count() == 0 or not query.strip():
        return []
    query_embedding = await get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count())
    )
    return results["documents"][0] if results["documents"] else []