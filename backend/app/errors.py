"""Domain errors and the contract error body: {"error": {"code", "message", "details"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel

log = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def not_found(code: str, message: str) -> AppError:
    return AppError(404, code, message)


def conflict(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(409, code, message, details)


def forbidden(message: str = "This action is not available for your account") -> AppError:
    return AppError(403, "forbidden", message)


def unauthenticated(message: str = "Please sign in to continue") -> AppError:
    return AppError(401, "unauthenticated", message)


def validation(fields: dict[str, str], message: str = "Some fields are invalid") -> AppError:
    return AppError(422, "validation_error", message, {"fields": fields})


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _field_name(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    if not parts:
        return "body"
    # Keep camelCase for already-aliased names; convert snake_case leftovers.
    return ".".join(p if not p.isidentifier() or "_" not in p else to_camel(p) for p in parts)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields: dict[str, str] = {}
        for err in exc.errors():
            name = _field_name(tuple(err.get("loc", ())))
            msg = "Unknown field" if err.get("type") == "extra_forbidden" else err.get("msg", "Invalid value")
            fields.setdefault(name, msg)
        return JSONResponse(error_body("validation_error", "Some fields are invalid", {"fields": fields}), status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(error_body("internal_error", "Something went wrong. Please try again."), status_code=500)
