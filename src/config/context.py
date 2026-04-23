from __future__ import annotations

from contextvars import ContextVar, Token

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


def bind_request_id(request_id: str) -> Token[str]:
    return _request_id_ctx.set(request_id)


def clear_request_id(token: Token[str]) -> None:
    _request_id_ctx.reset(token)
