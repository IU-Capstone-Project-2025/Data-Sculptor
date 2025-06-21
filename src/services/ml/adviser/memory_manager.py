"""Persistence layer for conversation memory combining Redis cache
and Postgres storage.
"""

import json
import uuid

import redis.asyncio as aioredis
import asyncpg
from settings import settings
from pydantic import UUID4


class MemoryManager:
    """Cache-aware helper for conversation history.

    Args:
        redis: Redis client used as the primary cache.
        pg: Asyncpg connection pool for durable storage.
    """
    def __init__(self, redis: aioredis.Redis, pg: asyncpg.Pool):
        self._redis = redis
        self._pg = pg
        self._limit = settings.token_limit

    async def _cache_key(self, conversation_id: UUID4) -> str:
        """Return the Redis key under which a conversation is cached.

        Args:
            conversation_id: Identifier of the conversation.

        Returns:
            str: A namespaced Redis key string.
        """
        return f"convo:{str(conversation_id)}"

    async def _history_from_cache(self, conversation_id: UUID4) -> list | None:
        """Fetch history from Redis; return *None* on a cache miss.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            list | None: Serialized history loaded from cache or *None* when absent.
        """
        raw = await self._redis.get(await self._cache_key(conversation_id))
        return json.loads(raw) if raw else None

    async def _history_from_pg(self, conversation_id: UUID4, max_tokens: int) -> list:
        """Retrieve the latest messages from Postgres within *max_tokens*.

        Args:
            conversation_id: Conversation identifier.
            max_tokens: Maximum cumulative tokens to fetch.

        Returns:
            list: History ordered oldest→newest bounded by *max_tokens*.
        """
        async with self._pg.acquire() as conn:
            rows = await conn.fetch(
                """
                with ranked as (
                    select role,
                           content,
                           token_count,
                           sum(token_count) over (order by created_at desc rows between unbounded preceding and current row) as cum_tokens
                    from messages
                    where conversation_id = $1
                    order by created_at desc
                )
                select role, content, token_count
                from ranked
                where cum_tokens <= $2
                order by cum_tokens desc
                """,
                conversation_id,
                max_tokens,
            )
        return [
            dict(role=r["role"], content=r["content"], token_count=r["token_count"])
            for r in rows
        ]

    def _trim(self, msgs: list[dict], max_tokens: int) -> list[dict]:
        """Return the newest messages whose cumulative token count fits *max_tokens*.

        Args:
            msgs: A full history list ordered oldest→newest.
            max_tokens: Token budget.

        Returns:
            list[dict]: Trimmed history satisfying the budget.
        """
        total = 0
        keep: list = []
        for m in reversed(msgs):
            if total + m["token_count"] > max_tokens:
                break
            total += m["token_count"]
            keep.append(m)
        keep.reverse()
        return keep

    async def get_history(self, conversation_id: UUID4, max_tokens: int) -> list[dict]:
        """Return cached conversation history.

        Args:
            conversation_id: Conversation identifier.
            max_tokens: Token budget for the history.

        Returns:
            list[dict]: History ordered oldest→newest.
        """
        cached = await self._history_from_cache(conversation_id)
        if cached is None:
            # cold start: load from DB and bubble into cache
            history = await self._history_from_pg(conversation_id, max_tokens)
            await self.save_history(conversation_id, history)
            return history

        # we have cache; return a trimmed view without mutating stored history
        return self._trim(cached, max_tokens)

    async def save_history(self, conversation_id: UUID4, history: list[dict]):
        """Persist a *trimmed* history snapshot to Redis.

        Args:
            conversation_id: Conversation identifier.
            history: Full history list ordered oldest→newest.
        """
        trimmed = self._trim(history, self._limit)
        await self._redis.set(
            await self._cache_key(conversation_id),
            json.dumps(trimmed, separators=(",", ":")),
        )

    async def save_messages(
        self,
        conversation_id: UUID4,
        user_id: UUID4,
        messages: list[tuple[str, str, int]],
    ):
        """Atomically write a conversation header (if new) and message rows.

        Args:
            conversation_id: Conversation identifier.
            user_id: Identifier of the message author.
            messages: List of `(role, content, token_count)` tuples.
        """
        async with self._pg.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    insert into conversations(id, user_id)
                    values($1, $2)
                    on conflict do nothing
                    """,
                    conversation_id,
                    user_id,
                )

                await conn.executemany(
                    """
                    insert into messages(id, conversation_id, role, content, token_count, created_at)
                    values($1, $2, $3, $4, $5, now())
                    """,
                    [
                        (
                            uuid.uuid4(),
                            conversation_id,
                            role,
                            content,
                            tokens,
                        )
                        for role, content, tokens in messages
                    ],
                )
