import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import IncidentReport, IncidentSeverity, IncidentSource
from .routers import admin_activity, auth, budget_requests, documents, expense_requests, health, incidents, operations, payments, quotations
from .services.audit import record_audit
from .services.incidents import incident_reference, safe_trace_summary


settings = get_settings()
logger = logging.getLogger("pimascor.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env in ("development", "test"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Correlation-ID"],
)


@app.middleware("http")
async def correlation_id(request: Request, call_next):
    request.state.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message, recovery, can_continue = friendly_http_error(exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
                "recovery": recovery,
                "canContinue": can_continue,
                "correlationId": getattr(request.state, "correlation_id", None),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    _: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INPUT_NEEDS_ATTENTION",
                "message": "Some information needs attention before this can be saved.",
                "recovery": "Review the marked fields, correct the information, and try again.",
                "canContinue": True,
                "correlationId": getattr(request.state, "correlation_id", None),
            }
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    reference: str | None = None
    incident_id: str | None = None
    try:
        with SessionLocal.begin() as db:
            incident = IncidentReport(
                reference=incident_reference(),
                actor_user_id=None,
                source=IncidentSource.SERVER,
                severity=IncidentSeverity.BLOCKING,
                operation="Complete a PIMASCOR operation",
                user_action=f"Using {request.method} {request.url.path}",
                user_message="We could not confirm whether the last action finished.",
                recovery_suggestion=(
                    "Stop here, check the relevant list for the record, and only then try once more."
                ),
                can_continue=False,
                page_path=request.headers.get("referer", request.url.path)[:240],
                request_method=request.method[:12],
                request_path=request.url.path[:240],
                http_status=500,
                error_code="UNEXPECTED_ERROR",
                technical_summary=safe_trace_summary(exc),
                client_runtime=None,
                deployment_tier=settings.deployment_tier,
                correlation_id=correlation_id,
            )
            db.add(incident)
            db.flush()
            record_audit(
                db,
                actor_user_id=None,
                action="INCIDENT_SERVER_DETECTED",
                entity_type="incident",
                entity_id=incident.id,
                correlation_id=correlation_id,
                reason=incident.reference,
            )
            reference = incident.reference
            incident_id = incident.id
    except Exception as reporting_error:
        logger.error(
            "Incident persistence failed for correlation %s (%s)",
            correlation_id,
            type(reporting_error).__name__,
        )
    logger.error(
        "Unhandled %s at %s %s; correlation=%s; incident=%s",
        type(exc).__name__,
        request.method,
        request.url.path,
        correlation_id,
        reference or "not-recorded",
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "UNEXPECTED_ERROR",
                "message": "We could not confirm whether your last action finished.",
                "recovery": (
                    "Stop here, check the relevant list for the record, and only then try once more."
                ),
                "canContinue": False,
                "correlationId": correlation_id,
                "incidentId": incident_id,
                "incidentReference": reference,
            }
        },
    )


def friendly_http_error(status_code: int, detail: object) -> tuple[str, str, bool]:
    detail_text = str(detail) if isinstance(detail, str) else ""
    if status_code == 401:
        if detail_text == "Invalid credentials":
            return (
                "The username or password could not be confirmed.",
                "Check the account details and try again.",
                True,
            )
        if "email code" in detail_text.lower():
            return (
                "That verification code could not be confirmed.",
                "Check the six digits and expiration time, then try again.",
                True,
            )
        return (
            "Your sign-in has expired.",
            "Sign in again, then return to this page.",
            False,
        )
    if status_code == 403:
        return (
            "Your account cannot complete this action.",
            "Stop here and ask the PIMASCOR Administrator to confirm your access.",
            False,
        )
    if status_code == 404:
        return (
            "We could not find that record.",
            "Refresh the list. The record may have been moved or removed.",
            True,
        )
    if status_code == 409:
        if "funding source already exists" in detail_text.lower():
            return (
                "That approved funding source is already on the list.",
                "Use the existing source, or enter a different approved display name.",
                True,
            )
        if "tax profile already exists" in detail_text.lower():
            return (
                "That tax profile is already configured.",
                "Review the existing profile before adding another one.",
                True,
            )
        return (
            "This record changed after you opened it.",
            "Refresh the record and review the latest information before trying again.",
            True,
        )
    if status_code == 413:
        return (
            "This file is larger than the 100 MB limit.",
            "Choose a smaller PDF, JPEG, or PNG file and upload it again.",
            True,
        )
    if status_code == 429:
        return (
            "There have been too many attempts in a short time.",
            "Wait a moment before trying again.",
            True,
        )
    if status_code >= 500:
        return (
            "The service could not complete this action.",
            "Stop here, check the relevant list, and try again after a short wait.",
            False,
        )
    safe_detail = detail_text
    message = safe_detail if safe_detail and len(safe_detail) <= 300 else "This action could not be completed."
    return message, "Review the information on this page and try again.", True


logging.basicConfig(level=logging.INFO)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(quotations.router, prefix=settings.api_prefix)
app.include_router(budget_requests.router, prefix=settings.api_prefix)
app.include_router(expense_requests.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)
app.include_router(operations.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(admin_activity.router, prefix=settings.api_prefix)
app.include_router(incidents.router, prefix=settings.api_prefix)
