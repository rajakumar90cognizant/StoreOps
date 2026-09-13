"""StoreOps FastAPI application entrypoint.

Every cross-module event subscriber is wired here, once, at import time --
this is the one file allowed to know that `alerts` reacts to `programmes`
and `activities` events. No module ever imports another module's service
directly for a *write*; this file is wiring, not a business rule.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.core.event_bus import event_bus
from app.modules.activities.routes import router as activities_router
from app.modules.activities.service import BULK_STATUS_UPDATED_EVENT
from app.modules.alerts.routes import router as alerts_router
from app.modules.alerts.service import alert_service
from app.modules.programmes.routes import router as programmes_router
from app.modules.programmes.service import MEMBER_ADDED_EVENT

app = FastAPI(title="StoreOps API", version="0.1.0")

app.include_router(activities_router)
app.include_router(programmes_router)
app.include_router(alerts_router)

event_bus.subscribe(MEMBER_ADDED_EVENT, alert_service.handle_programme_member_added)
event_bus.subscribe(BULK_STATUS_UPDATED_EVENT, alert_service.handle_activity_bulk_status_updated)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
