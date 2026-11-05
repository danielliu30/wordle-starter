"""
Tests for error handlers, exercised through the ASGI app (no httpx in the venv).
"""
import asyncio
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from app.middleware.error_handler import register_exception_handlers


class Guess(BaseModel):
    word: str

    @field_validator("word")
    @classmethod
    def check_word(cls, v):
        if v != "crane":
            raise ValueError("invalid word")
        return v


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/limited")
    def limited():
        raise HTTPException(status_code=429, detail="Slow down", headers={"Retry-After": "5"})

    @app.get("/only-get")
    def only_get():
        return {}

    @app.post("/guess")
    def guess(body: Guess):
        return body

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    return app


def call(app, method, path, body=b""):
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "path": path, "raw_path": path.encode(), "query_string": b"",
        "headers": [(b"content-type", b"application/json")], "server": ("test", 80),
        "client": ("test", 1), "scheme": "http", "root_path": "",
    }
    sent = []
    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    async def run():
        try:
            await app(scope, receive, send)
        except Exception:
            pass  # ServerErrorMiddleware re-raises after sending the 500 response

    asyncio.run(run())
    start = next(m for m in sent if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    headers = {k.decode().lower(): v.decode() for k, v in start["headers"]}
    return start["status"], headers, json.loads(payload)


def assert_error_shape(body, code):
    assert set(body) == {"error"}
    error = body["error"]
    assert error["code"] == code
    assert {"message", "details", "request_id", "timestamp"} <= set(error)
    assert error["timestamp"].endswith("Z")


def test_unknown_route_uses_standard_format():
    status, _, body = call(make_app(), "GET", "/missing")
    assert status == 404
    assert_error_shape(body, "HTTP_ERROR")
    assert body["error"]["message"] == "Not Found"


def test_main_app_registers_handlers():
    from main import app

    status, _, body = call(app, "GET", "/missing")
    assert status == 404
    assert_error_shape(body, "HTTP_ERROR")


def test_http_exception_headers_are_forwarded():
    status, headers, body = call(make_app(), "GET", "/limited")
    assert status == 429
    assert headers["retry-after"] == "5"
    assert_error_shape(body, "HTTP_ERROR")


def test_method_not_allowed_keeps_allow_header():
    status, headers, _ = call(make_app(), "POST", "/only-get")
    assert status == 405
    assert headers["allow"] == "GET"


def test_validator_value_error_returns_422():
    status, _, body = call(make_app(), "POST", "/guess", json.dumps({"word": "abcde"}).encode())
    assert status == 422
    assert_error_shape(body, "VALIDATION_ERROR")
    assert body["error"]["details"][0]["msg"] == "Value error, invalid word"


def test_unhandled_exception_returns_500():
    status, _, body = call(make_app(), "GET", "/boom")
    assert status == 500
    assert_error_shape(body, "INTERNAL_ERROR")
