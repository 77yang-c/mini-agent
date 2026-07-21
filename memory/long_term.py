import uuid
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer


class LongMemory:
    """长期记忆：ChromaDB + MiniLM embedding"""

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.db = chromadb.PersistentClient(path="./memory_db")
        self.collection = self.db.get_or_create_collection("memories")

    def remember(self, content: str, tags: list[str] = None):
        vec = self.model.encode(content).tolist()
        self.collection.add(
            embeddings=[vec],
            documents=[content],
            metadatas=[{"tags": ",".join(tags or []), "time": datetime.now().isoformat()}],
            ids=[str(uuid.uuid4())]
        )

    def recall(self, query: str, top_k=3) -> list[str]:
        vec = self.model.encode(query).tolist()
        results = self.collection.query(query_embeddings=[vec], n_results=top_k)
        return results.get("documents", [[]])[0]
