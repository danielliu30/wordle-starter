"""
Tests for error handlers
"""
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from app.middleware.error_handler import http_exception_handler, validation_exception_handler, general_exception_handler


async def test_http_exception_handler():
    """Test HTTP exception returns correct format"""
    request = Request({"type": "http", "method": "GET", "headers": {}, "query_string": "", "path": "/test"})
    request.state.request_id = "test-id"
    exc = HTTPException(status_code=404, detail="Not found")
    response = await http_exception_handler(request, exc)
    assert response.status_code == 404


async def test_validation_exception_handler():
    """Test validation error returns 422 with details"""
    request = Request({"type": "http", "method": "POST", "headers": {}, "query_string": "", "path": "/test"})
    request.state.request_id = "test-id"
    error = RequestValidationError(errors=[{"loc": ["body", "field"], "msg": "required"}])
    response = await validation_exception_handler(request, error)
    assert response.status_code == 422


async def test_general_exception_handler():
    """Test general exception returns 500"""
    request = Request({"type": "http", "method": "GET", "headers": {}, "query_string": "", "path": "/test"})
    request.state.request_id = "test-id"
    exc = Exception("Error")
    response = await general_exception_handler(request, exc)
    assert response.status_code == 500
