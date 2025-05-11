"""API routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.presentation.deps import get_templates
from app.presentation.routes.prompts import router as prompts_router
from app.presentation.routes.monitors import router as monitors_router


def get_routes():
    """Get all route handlers."""
    return [
        home_router,
        prompts_router,
        monitors_router,
    ]


home_router = APIRouter()


@home_router.get("/", response_class=HTMLResponse)
async def index(request: Request, templates=Depends(get_templates)):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request})