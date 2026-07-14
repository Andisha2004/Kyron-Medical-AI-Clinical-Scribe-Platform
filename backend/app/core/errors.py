from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error_response(
    request: Request,
    *,
    status_code: int,
    message: str,
    details: object | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "path": request.url.path,
            "timestamp": datetime.now(UTC).isoformat(),
            "errors": details,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict):
            message = str(exc.detail.get("message", "Request failed."))
            details = exc.detail.get("errors")
            if details is None:
                details = {
                    key: value
                    for key, value in exc.detail.items()
                    if key != "message"
                } or None
            return _error_response(
                request,
                status_code=exc.status_code,
                message=message,
                details=details,
            )

        return _error_response(
            request,
            status_code=exc.status_code,
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed.",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error.",
            details={"exception_type": exc.__class__.__name__},
        )
