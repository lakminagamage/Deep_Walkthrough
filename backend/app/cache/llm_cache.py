from __future__ import annotations

import hashlib
import json
from typing import Sequence

import redis.asyncio as aioredis
from langchain_core.caches import BaseCache
from langchain_core.outputs import Generation


class RedisLLMCache(BaseCache):
    """Redis-backed async LangChain cache. Key = sha256(llm_string + prompt)."""

    def __init__(self, redis_url: str, ttl: int) -> None:
        self._redis_url = redis_url
        self._ttl = ttl
        self._client: aioredis.Redis | None = None

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def _key(self, prompt: str, llm_string: str) -> str:
        raw = f"{llm_string}::{prompt}"
        return "llmcache:" + hashlib.sha256(raw.encode()).hexdigest()

    # ── Sync stubs — never called in our fully-async pipeline ─────────────────

    def lookup(self, prompt: str, llm_string: str) -> list[Generation] | None:
        return None

    def update(self, prompt: str, llm_string: str, return_val: Sequence[Generation]) -> None:
        pass

    def clear(self, **kwargs) -> None:
        pass

    # ── Async implementations ─────────────────────────────────────────────────

    async def alookup(self, prompt: str, llm_string: str) -> list[Generation] | None:
        raw = await self._get_client().get(self._key(prompt, llm_string))
        if raw is None:
            return None
        return [Generation(**g) for g in json.loads(raw)]

    async def aupdate(
        self,
        prompt: str,
        llm_string: str,
        return_val: Sequence[Generation],
    ) -> None:
        serialized = json.dumps([g.dict() for g in return_val])
        await self._get_client().setex(self._key(prompt, llm_string), self._ttl, serialized)

    async def aclear(self, **kwargs) -> None:
        await self._get_client().flushdb()
