# -*- coding: utf-8 -*-

from agent_app.runtimes.fallback_model import FallbackAnthropicModel
from agent_app.runtimes.fallback_model import add_usage
from agent_app.runtimes.fallback_model import block_index_of
from agent_app.runtimes.fallback_model import drop_declined_blocks
from agent_app.runtimes.fallback_model import stop_reason_of

import asyncio

import pytest
from strands.event_loop.streaming import process_stream
from strands.models.anthropic import AnthropicModel

from agent_app.audit.audit_agent import ModelLog

PRIMARY = "acme-widget-model-2"
FALLBACK = "acme-widget-model-1"


# The events of a model call, as the Anthropic SDK dumps them.
def start(model: str) -> dict:
    return {"type": "message_start", "message": {"model": model}}


def thinking(index: int, signature: str) -> list[dict]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "thinking_delta", "thinking": f"thought {signature}"},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "signature_delta", "signature": signature},
        },
        {"type": "content_block_stop", "index": index},
    ]


def text(index: int, value: str) -> list[dict]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "text", "text": ""},
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": value},
        },
        {"type": "content_block_stop", "index": index},
    ]


def tool_use(index: int, tool_use_id: str) -> list[dict]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "tool_use",
                "id": tool_use_id,
                "name": "count_widgets",
                "input": {},
            },
        },
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "input_json_delta", "partial_json": '{"bin": 7}'},
        },
        {"type": "content_block_stop", "index": index},
    ]


def fallback(index: int) -> list[dict]:
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {
                "type": "fallback",
                "from": {"model": PRIMARY},
                "to": {"model": FALLBACK},
            },
        },
        {"type": "content_block_stop", "index": index},
    ]


def stop(stop_reason: str, output_tokens: int = 10) -> list[dict]:
    return [
        {"type": "message_stop", "message": {"stop_reason": stop_reason}},
        {
            "type": "metadata",
            "usage": {"input_tokens": 100, "output_tokens": output_tokens},
        },
    ]


def flatten(*parts) -> list[dict]:
    events = []
    for part in parts:
        events.extend(part if isinstance(part, list) else [part])
    return events


@pytest.fixture
def scripted(monkeypatch):
    """
    Replace the network call of ``AnthropicModel.stream`` with scripted
    attempts: each call formats the events of the next attempt, as the real
    method does, and notes the model it was made on.
    """
    attempts: list[list[dict]] = []
    asked: list[str] = []

    async def stream(self, *args, **kwargs):
        asked.append(self.config["model_id"])
        for event in attempts.pop(0):
            yield self.format_chunk(event)

    monkeypatch.setattr(AnthropicModel, "stream", stream)
    return attempts, asked


def make_model(
    fallback_model_id: str | None = FALLBACK,
    model_log: ModelLog | None = None,
) -> FallbackAnthropicModel:
    return FallbackAnthropicModel(
        fallback_model_id=fallback_model_id,
        model_log=model_log,
        client_args={"api_key": "fake-key"},
        model_id=PRIMARY,
        max_tokens=100,
    )


def run(model: FallbackAnthropicModel) -> tuple[str, dict, dict]:
    """
    One model call, assembled into a message the way the Strands event loop
    does it; returns the stop reason, the message, and the usage.
    """

    async def collect():
        last = None
        async for event in process_stream(model.stream([], None, None)):
            last = event
        return last["stop"]

    stop_reason, message, usage, _ = asyncio.run(collect())
    return stop_reason, message, usage


def kinds(message: dict) -> list[str]:
    return [next(iter(block)) for block in message["content"]]


def test_block_index_of():
    assert block_index_of({"contentBlockStart": {"contentBlockIndex": 2}}) == 2
    assert block_index_of({"contentBlockDelta": {"contentBlockIndex": 0}}) == 0
    assert block_index_of({"contentBlockStop": {"contentBlockIndex": 5}}) == 5
    assert block_index_of({"messageStart": {"role": "assistant"}}) is None


def test_stop_reason_of():
    chunks = [{"messageStart": {}}, {"messageStop": {"stopReason": "tool_use"}}]
    assert stop_reason_of(chunks) == "tool_use"
    assert stop_reason_of([{"messageStart": {}}]) is None


def test_drop_declined_blocks():
    chunks = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"contentBlockStart": {"contentBlockIndex": 1}},
        {"contentBlockStop": {"contentBlockIndex": 1}},
        {"contentBlockStart": {"contentBlockIndex": 2}},
        {"contentBlockStart": {"contentBlockIndex": 3}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]
    # no fallback: nothing is dropped
    block_types = {0: "thinking", 1: "text", 2: "tool_use", 3: "text"}
    assert drop_declined_blocks(chunks, block_types) == chunks
    # a fallback before anything was written: nothing is dropped
    block_types = {0: "fallback", 1: "thinking", 2: "tool_use", 3: "text"}
    assert drop_declined_blocks(chunks, block_types) == chunks
    # before the fallback, only text stays
    block_types = {0: "thinking", 1: "text", 2: "fallback", 3: "thinking"}
    kept = drop_declined_blocks(chunks, block_types)
    assert [block_index_of(chunk) for chunk in kept] == [None, 1, 1, 2, 3, None]
    # the last fallback is the boundary
    block_types = {0: "fallback", 1: "tool_use", 2: "fallback", 3: "thinking"}
    kept = drop_declined_blocks(chunks, block_types)
    assert [block_index_of(chunk) for chunk in kept] == [None, 2, 3, None]


def test_add_usage():
    declined = [
        {"metadata": {"usage": {"inputTokens": 100, "cacheReadInputTokens": 7}}}
    ]
    chunks = [
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 50, "outputTokens": 9}, "metrics": {}}},
    ]
    assert add_usage(chunks, declined) == [
        {"messageStop": {"stopReason": "end_turn"}},
        {
            "metadata": {
                "usage": {
                    "inputTokens": 150,
                    "outputTokens": 9,
                    "cacheReadInputTokens": 7,
                },
                "metrics": {},
            }
        },
    ]
    # the declined attempt reported no usage
    assert add_usage(chunks, [{"messageStop": {"stopReason": "refusal"}}]) == chunks
    # the answering attempt reported none: there is nothing to add to
    assert add_usage(chunks[:1], declined) == chunks[:1]


class TestFallbackAnthropicModel:
    def test_plain_call(self, scripted):
        """Without a fallback the message is what the model wrote."""
        attempts, asked = scripted
        attempts.append(
            flatten(
                start(PRIMARY),
                thinking(0, "sig-a"),
                tool_use(1, "tool-1"),
                stop("tool_use"),
            )
        )
        log = ModelLog()
        stop_reason, message, usage = run(make_model(model_log=log))
        assert stop_reason == "tool_use"
        assert kinds(message) == ["reasoningContent", "toolUse"]
        assert usage["outputTokens"] == 10
        assert asked == [PRIMARY]
        assert log.models == [PRIMARY]

    def test_fallback_before_any_output(self, scripted):
        """The fallback model wrote all of it: all of it stays."""
        attempts, asked = scripted
        attempts.append(
            flatten(
                start(FALLBACK),
                fallback(0),
                thinking(1, "sig-b"),
                tool_use(2, "tool-1"),
                stop("tool_use"),
            )
        )
        stop_reason, message, _ = run(make_model())
        assert stop_reason == "tool_use"
        assert kinds(message) == ["reasoningContent", "toolUse"]
        assert asked == [PRIMARY]

    def test_fallback_after_output(self, scripted):
        """
        What the declined model thought and called is gone, so the next model
        call does not send back a thinking block from each side of the fallback.
        """
        attempts, asked = scripted
        attempts.append(
            flatten(
                start(PRIMARY),
                thinking(0, "sig-a"),
                text(1, "Looking at bin 7."),
                tool_use(2, "tool-declined"),
                fallback(3),
                thinking(4, "sig-b"),
                tool_use(5, "tool-1"),
                stop("tool_use"),
            )
        )
        log = ModelLog()
        stop_reason, message, _ = run(make_model(model_log=log))
        assert stop_reason == "tool_use"
        assert kinds(message) == ["text", "reasoningContent", "toolUse"]
        # the call began on one model and was answered by the other
        assert log.models == [FALLBACK]
        reasoning = message["content"][1]["reasoningContent"]["reasoningText"]
        assert reasoning["signature"] == "sig-b"
        assert message["content"][2]["toolUse"]["toolUseId"] == "tool-1"
        assert asked == [PRIMARY]

    def test_refusal_is_retried_on_the_fallback_model(self, scripted):
        """
        The declined attempt is discarded whole, its tool call included, and
        the model of the config is the configured one again afterwards.
        """
        attempts, asked = scripted
        attempts.append(
            flatten(
                start(PRIMARY),
                thinking(0, "sig-a"),
                tool_use(1, "tool-declined"),
                stop("refusal", output_tokens=30),
            )
        )
        attempts.append(
            flatten(
                start(FALLBACK),
                thinking(0, "sig-b"),
                tool_use(1, "tool-1"),
                stop("tool_use"),
            )
        )
        log = ModelLog()
        model = make_model(model_log=log)
        stop_reason, message, usage = run(model)
        assert stop_reason == "tool_use"
        assert kinds(message) == ["reasoningContent", "toolUse"]
        assert message["content"][1]["toolUse"]["toolUseId"] == "tool-1"
        assert asked == [PRIMARY, FALLBACK]
        # the declined attempt answered nothing: only the second model is noted
        assert log.models == [FALLBACK]
        assert model.get_config()["model_id"] == PRIMARY
        # both attempts were paid for
        assert usage["inputTokens"] == 200
        assert usage["outputTokens"] == 40

    def test_fallback_model_refuses_too(self, scripted):
        """One retry, then the refusal is the answer."""
        attempts, asked = scripted
        attempts.append(flatten(start(PRIMARY), stop("refusal")))
        attempts.append(flatten(start(FALLBACK), stop("refusal")))
        stop_reason, message, _ = run(make_model())
        assert stop_reason == "refusal"
        assert message["content"] == []
        assert asked == [PRIMARY, FALLBACK]

    def test_retry_fails(self, scripted):
        """The model of the config is restored even when the retry raises."""
        attempts, asked = scripted
        attempts.append(flatten(start(PRIMARY), stop("refusal")))
        attempts.append([{"type": "no_such_event"}])
        model = make_model()
        with pytest.raises(RuntimeError, match="unknown type"):
            run(model)
        assert asked == [PRIMARY, FALLBACK]
        assert model.get_config()["model_id"] == PRIMARY

    @pytest.mark.parametrize("fallback_model_id", [None, PRIMARY])
    def test_refusal_without_another_model(self, scripted, fallback_model_id):
        """No fallback model, or the same model: the refusal is returned."""
        attempts, asked = scripted
        attempts.append(flatten(start(PRIMARY), stop("refusal")))
        stop_reason, _, _ = run(make_model(fallback_model_id))
        assert stop_reason == "refusal"
        assert asked == [PRIMARY]


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.runtimes.fallback_model",
        preview=False,
    )
