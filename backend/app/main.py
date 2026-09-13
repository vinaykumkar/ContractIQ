"""ContractIQ FastAPI application factory.

- all routes under /api; OpenAPI docs at /docs, /redoc, /openapi.json
- request-id middleware (X-Request-ID) shared with logs and error envelopes
- domain exceptions mapped to consistent JSON errors (never raw tracebacks)
- CORS restricted to configured origins (default: local Vite dev server)
- the ML analyzer is a per-process lazy singleton (loaded once, kept on device)
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.deps import build_service, request_id_var
from .api.router import api_router
from .core.config import Settings, load_settings
from .core.exceptions import (
    AnalysisFailure,
    AnalysisInProgress,
    ContractIQError,
    ContractNotFound,
    CorruptDocument,
    DatabaseFailure,
    EmptyDocument,
    EmptyFileError,
    EncryptedDocument,
    FileTooLarge,
    InvalidFilename,
    ModelUnavailable,
    OcrRequiredError,
    ParseError,
    RawTextUnavailable,
    UnsupportedFileType,
)
from .core.logging import get_logger, log_event

logger = get_logger()

APP_NAME = "ContractIQ API"
APP_VERSION = "0.5.0"

# domain exception -> (http status, error code)
_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    UnsupportedFileType: (400, "UNSUPPORTED_FILE_TYPE"),
    FileTooLarge: (413, "FILE_TOO_LARGE"),
    EmptyFileError: (400, "EMPTY_FILE"),
    InvalidFilename: (400, "INVALID_FILENAME"),
    CorruptDocument: (422, "CORRUPT_DOCUMENT"),
    EncryptedDocument: (422, "ENCRYPTED_DOCUMENT"),
    EmptyDocument: (422, "EMPTY_DOCUMENT"),
    OcrRequiredError: (422, "OCR_REQUIRED"),
    ParseError: (422, "PARSE_ERROR"),
    ContractNotFound: (404, "CONTRACT_NOT_FOUND"),
    RawTextUnavailable: (404, "RAW_TEXT_UNAVAILABLE"),
    ModelUnavailable: (503, "MODEL_UNAVAILABLE"),
    AnalysisFailure: (500, "ANALYSIS_FAILURE"),
    AnalysisInProgress: (409, "ANALYSIS_IN_PROGRESS"),
    DatabaseFailure: (500, "DATABASE_FAILURE"),
}


def _error_response(status: int, code: str, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": code, "message": message, "request_id": request_id},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_storage_dirs()
        # initialize the database schema once (idempotent; never deletes data)
        from .db.database import get_engine, init_db

        app.state.engine = get_engine(settings.database_url)
        init_db(app.state.engine)
        # analyzer singleton: created now, model loads lazily on first analysis
        app.state.settings = settings
        app.state.service = build_service(settings)
        # crash recovery: analyses stuck in ANALYZING from a previous process
        app.state.service.recover_stale_analyses()
        log_event(logger, "startup", version=APP_VERSION, db="configured")
        yield
        try:
            app.state.service.close()  # dispose the service's lazily-created engine
        except Exception:
            pass
        try:
            app.state.engine.dispose()
        except Exception:
            pass
        log_event(logger, "shutdown")

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="AI-assisted contract intelligence and risk analysis. "
                    "Results should be reviewed by a qualified professional.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request_id_var.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(ContractIQError)
    async def domain_error_handler(request: Request, exc: ContractIQError):
        for cls in type(exc).__mro__:
            if cls in _ERROR_MAP:
                status, code = _ERROR_MAP[cls]
                break
        else:  # pragma: no cover
            status, code = 500, "CONTRACTIQ_ERROR"
        log_event(logger, "error", request_id_var.get(), code=code, message=exc.message)
        return _error_response(status, code, exc.message, request_id_var.get())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(422, "VALIDATION_ERROR",
                               "Request validation failed.", request_id_var.get())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        # log the traceback server-side only; clients get a safe envelope
        logger.exception("unhandled error") if logger.isEnabledFor(logging.DEBUG) else None
        log_event(logger, "error", request_id_var.get(), code="INTERNAL_ERROR",
                  message=type(exc).__name__)
        return _error_response(500, "INTERNAL_ERROR",
                               "An unexpected error occurred.", request_id_var.get())

    app.include_router(api_router)

    # Production single-port serving: when a built frontend exists at
    # frontend/dist, serve it from this process (API stays under /api;
    # all other GETs fall back to index.html so SPA deep links resolve).
    dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if (dist_dir / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            if full_path.startswith("api"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            candidate = dist_dir / full_path
            if full_path and candidate.is_file() and candidate.parent == dist_dir:
                return FileResponse(candidate)  # root-level files, e.g. favicon
            return FileResponse(dist_dir / "index.html")

    return app


app = create_app()
