from __future__ import annotations

import chromadb
from openai import AsyncOpenAI

from app.config import CHROMA_HOST, CHROMA_PORT


class LongTermMemory:
    """Async ChromaDB client wrapping two collections: 'documents' and 'reports'."""

    def __init__(self, host: str = CHROMA_HOST, port: int = CHROMA_PORT) -> None:
        self._host = host
        self._port = port
        self._client: chromadb.AsyncClientAPI | None = None
        self._openai = AsyncOpenAI()

    async def _get_client(self) -> chromadb.AsyncClientAPI:
        if self._client is None:
            self._client = await chromadb.AsyncHttpClient(host=self._host, port=self._port)
        return self._client

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [e.embedding for e in resp.data]

    async def _collection(self, name: str):
        client = await self._get_client()
        return await client.get_or_create_collection(name=name)

    # ── Public API ────────────────────────────────────────────────────────────

    async def query(
        self,
        collection: str,
        query: str,
        top_k: int = 10,
        session_id: str | None = None,
    ) -> list[dict]:
        embeddings = await self._embed([query])
        col = await self._collection(collection)
        kwargs: dict = {"query_embeddings": embeddings, "n_results": top_k}
        if session_id:
            kwargs["where"] = {"session_id": session_id}
        try:
            results = await col.query(**kwargs)
        except Exception:
            return []

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        return [
            {
                "id": ids[i],
                "document": docs[i] if docs else "",
                "metadata": metas[i] if metas else {},
                "distance": dists[i] if dists else None,
            }
            for i in range(len(ids))
        ]

    async def store(self, collection: str, documents: list[dict]) -> None:
        """Store documents. Each dict must have 'chunk_id' and 'content' keys."""
        texts = [d["content"] for d in documents]
        embeddings = await self._embed(texts)
        col = await self._collection(collection)
        await col.add(
            ids=[d["chunk_id"] for d in documents],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {k: v for k, v in d.items() if k not in ("content", "chunk_id") and v is not None}
                for d in documents
            ],
        )

    async def get_by_ids(self, collection: str, ids: list[str]) -> list[dict]:
        """Fetch documents by their exact IDs."""
        if not ids:
            return []
        col = await self._collection(collection)
        results = await col.get(ids=ids, include=["documents", "metadatas"])
        out_ids = results.get("ids", [])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        return [
            {
                "id": out_ids[i],
                "document": docs[i] if docs else "",
                "metadata": metas[i] if metas else {},
            }
            for i in range(len(out_ids))
        ]

    async def delete(self, collection: str, ids: list[str]) -> None:
        col = await self._collection(collection)
        await col.delete(ids=ids)
