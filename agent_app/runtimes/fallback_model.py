# -*- coding: utf-8 -*-

"""
The Strands Anthropic model, made to live with a model call that Claude's
safety classifiers decline.

:data:`~agent_app.runtimes.audit_agent.FALLBACK_PARAMS` asks the Anthropic API
to rerun a declined call on a fallback model inside the same call. That
leaves two cases Strands' own ``AnthropicModel`` does not handle, both met in
the evaluation of 2026-11-21:

- **The fallback happens after the first model already wrote something.** The
  response is then one message with a ``fallback`` content block in the
  middle: before it what the declined model wrote, after it what the fallback
  model wrote. The API refuses to be sent that message back unless everything
  before the block except text is left out: with a ``thinking`` block on each
  side and no ``fallback`` block between them, which is what Strands keeps,
  the next model call fails with a 400 (``thinking`` blocks "cannot be
  modified"). :func:`drop_declined_blocks` leaves those blocks out before
  Strands sees them, so a tool call the declined model wrote is not run either.
- **The API returns the refusal instead of falling back.** It does when the
  declined model had already written a tool call. The call is then made again
  here, on ``fallback_model_id``, and what the declined model wrote is
  discarded.

To do either, a model call's response is read to its end before any of it is
passed on. The agent answers once, when it is done, so nothing is lost.
"""

from __future__ import annotations

import typing as T
import logging

from strands.models.anthropic import AnthropicModel

from .common import STOP_REASON_REFUSAL

logger = logging.getLogger(__name__)

#: The content block the Anthropic API puts where one model's output ends and
#: the fallback model's begins.
FALLBACK_BLOCK = "fallback"

#: The only kind of content block that may be sent back when it comes before a
#: :data:`FALLBACK_BLOCK`.
TEXT_BLOCK = "text"

_BLOCK_CHUNK_KEYS = ["contentBlockStart", "contentBlockDelta", "contentBlockStop"]


def block_index_of(chunk: dict) -> int | None:
    """
    The index of the content block a Strands stream chunk belongs to; None for
    a chunk about the message as a whole.
    """
    for key in _BLOCK_CHUNK_KEYS:
        if key in chunk:
            return chunk[key]["contentBlockIndex"]
    return None


def stop_reason_of(chunks: list[dict]) -> str | None:
    """
    Why the model call of ``chunks`` stopped; None if it never said.
    """
    for chunk in chunks:
        if "messageStop" in chunk:
            return chunk["messageStop"]["stopReason"]
    return None


def drop_declined_blocks(chunks: list[dict], block_types: dict[int, str]) -> list[dict]:
    """
    ``chunks`` without the content blocks a declined model wrote before the
    fallback model took over: every block before the last
    :data:`FALLBACK_BLOCK` that is not text. Unchanged when no fallback
    happened, or when it happened before anything was written.

    :param block_types: the type of each content block of the response, by its
        index, as the Anthropic API named it.
    """
    boundaries = [
        index
        for index, block_type in block_types.items()
        if block_type == FALLBACK_BLOCK
    ]
    if not boundaries:
        return chunks
    boundary = max(boundaries)
    declined = {
        index
        for index, block_type in block_types.items()
        if index < boundary and block_type != TEXT_BLOCK
    }
    return [chunk for chunk in chunks if block_index_of(chunk) not in declined]


def add_usage(chunks: list[dict], declined: list[dict]) -> list[dict]:
    """
    ``chunks`` with the token counts of the ``declined`` attempt added to its
    own: the declined attempt was paid for too. Unchanged when either attempt
    reported no usage.
    """
    spent = [chunk["metadata"]["usage"] for chunk in declined if "metadata" in chunk]
    if not spent:
        return chunks
    result = []
    for chunk in chunks:
        if "metadata" in chunk:
            usage = dict(chunk["metadata"]["usage"])
            for key, value in spent[0].items():
                usage[key] = usage.get(key, 0) + value
            chunk = {"metadata": {**chunk["metadata"], "usage": usage}}
        result.append(chunk)
    return result


class FallbackAnthropicModel(AnthropicModel):
    """
    ``AnthropicModel`` whose model calls survive a refusal of the configured
    model; see the module's docstring for the two cases.

    :param fallback_model_id: the Claude model a call is made again on when
        the API returns the configured model's refusal; None to return the
        refusal as it is. For a ``cyber`` refusal of ``claude-sonnet-5-5`` the
        API itself falls back to ``claude-sonnet-5``.
    """

    def __init__(self, *, fallback_model_id: str | None = None, **kwargs: T.Any):
        super().__init__(**kwargs)
        self.fallback_model_id = fallback_model_id
        self._block_types: dict[int, str] = {}

    def format_chunk(self, event: dict[str, T.Any]) -> T.Any:
        """
        As ``AnthropicModel`` formats it; the type of every content block is
        noted on the way, since the formatted chunk no longer says it.
        """
        if event["type"] == "content_block_start":
            self._block_types[event["index"]] = event["content_block"]["type"]
        return super().format_chunk(event)

    async def _attempt(self, args: tuple, kwargs: dict) -> list[dict]:
        """
        One model call on the model of the config, read to its end, without
        what a declined model wrote before a fallback.
        """
        self._block_types = {}
        chunks = []
        async for chunk in super().stream(*args, **kwargs):
            chunks.append(chunk)
        return drop_declined_blocks(chunks, self._block_types)

    async def stream(self, *args: T.Any, **kwargs: T.Any) -> T.AsyncGenerator:
        """
        As ``AnthropicModel.stream``, except that the chunks arrive together
        once the call is over, and that a call the configured model refuses is
        made once more on ``fallback_model_id``. If that model refuses too, its
        refusal is what the caller gets.
        """
        chunks = await self._attempt(args, kwargs)
        model_id = self.config["model_id"]
        refused = stop_reason_of(chunks) == STOP_REASON_REFUSAL
        if refused and self.fallback_model_id not in (None, model_id):
            logger.warning(
                "model_id=<%s>, fallback_model_id=<%s> | the model declined and "
                "the API did not fall back, calling the fallback model",
                model_id,
                self.fallback_model_id,
            )
            self.update_config(model_id=self.fallback_model_id)
            try:
                retried = await self._attempt(args, kwargs)
            finally:
                self.update_config(model_id=model_id)
            chunks = add_usage(retried, chunks)
        for chunk in chunks:
            yield chunk
