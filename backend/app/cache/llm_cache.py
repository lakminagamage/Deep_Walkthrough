from __future__ import annotations

import hashlib
import json
from typing import Sequence

import redis.asyncio as aioredis
from langchain_core.caches import BaseCache
from langchain_core.messages import messages_from_dict, message_to_dict
from langchain_core.outputs import ChatGeneration, Generation


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

    # ── Sync stubs — never called in our fully-async pipeline 

    def lookup(self, prompt: str, llm_string: str) -> list[Generation] | None:
        return None

    def update(self, prompt: str, llm_string: str, return_val: Sequence[Generation]) -> None:
        pass

    def clear(self, **kwargs) -> None:
        pass

    # ── Async implementations ──

    async def alookup(self, prompt: str, llm_string: str) -> list[Generation] | None:
        raw = await self._get_client().get(self._key(prompt, llm_string))
        if raw is None:
            return None
        result: list[Generation] = []
        for g in json.loads(raw):
            if g.get("type") == "ChatGeneration":
                msg_data = g.get("message", {})
                # Handle both serialization formats:
                # new: {"type": "ai", "data": {...}}  (from message_to_dict)
                # old: {"type": "ai", "content": ...} (from .dict())
                if "data" not in msg_data:
                    msg_data = {"type": msg_data.get("type", "ai"), "data": msg_data}
                message = messages_from_dict([msg_data])[0]
                result.append(ChatGeneration(
                    text=g.get("text", ""),
                    message=message,
                    generation_info=g.get("generation_info"),
                ))
            else:
                result.append(Generation(
                    text=g.get("text", ""),
                    generation_info=g.get("generation_info"),
                ))
        return result

    async def aupdate(
        self,
        prompt: str,
        llm_string: str,
        return_val: Sequence[Generation],
    ) -> None:
        entries = []
        for g in return_val:
            if isinstance(g, ChatGeneration):
                entries.append({
                    "type": "ChatGeneration",
                    "text": g.text,
                    "generation_info": g.generation_info,
                    "message": message_to_dict(g.message),
                })
            else:
                entries.append({
                    "type": "Generation",
                    "text": g.text,
                    "generation_info": g.generation_info,
                })
        await self._get_client().setex(
            self._key(prompt, llm_string), self._ttl, json.dumps(entries)
        )

    async def aclear(self, **kwargs) -> None:
        await self._get_client().flushdb()
