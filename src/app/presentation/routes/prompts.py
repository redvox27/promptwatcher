"""Routes for handling prompts."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.domain.models import PromptRecord
from app.domain.repositories import PromptRepository
from app.domain.services import PromptCaptureService
from app.presentation.deps import get_prompt_capture_service, get_prompt_repository, get_templates


class PromptCreate(BaseModel):
    """DTO for creating a prompt."""
    
    prompt_text: str
    response_text: str
    project_name: str = Field(default="default")
    project_goal: str = Field(default="default")
    terminal_type: str = Field(default="Terminal")


class PromptResponse(BaseModel):
    """DTO for prompt response."""
    
    id: UUID
    prompt_text: str
    response_text: str
    project_name: str
    project_goal: str
    timestamp: datetime
    terminal_type: str
    session_id: Optional[UUID] = None
    labels: List[str] = Field(default_factory=list)
    
    class Config:
        """Pydantic config."""
        
        from_attributes = True


class PromptListResponse(BaseModel):
    """DTO for paginated prompt list response."""
    
    items: List[PromptResponse]
    total: int
    limit: int
    offset: int


class LabelCreate(BaseModel):
    """DTO for creating a label."""
    
    label: str


router = APIRouter()


@router.post("/api/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    prompt: PromptCreate,
    capture_service: PromptCaptureService = Depends(get_prompt_capture_service),
    repository: PromptRepository = Depends(get_prompt_repository),
):
    """
    Create a new prompt record.
    
    Args:
        prompt: Prompt data
        capture_service: Prompt capture service
        repository: Prompt repository
        
    Returns:
        Created prompt record
    """
    try:
        # Capture the prompt
        record = await capture_service.capture_prompt(
            prompt_text=prompt.prompt_text,
            response_text=prompt.response_text,
            project_name=prompt.project_name,
            project_goal=prompt.project_goal,
            terminal_type=prompt.terminal_type,
        )
        
        # Save to repository
        saved_record = await repository.add(record)
        
        return saved_record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/prompts", response_model=PromptListResponse)
async def list_prompts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    project_name: Optional[str] = None,
    repository: PromptRepository = Depends(get_prompt_repository),
):
    """
    List prompt records with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        project_name: Filter by project name
        repository: Prompt repository
        
    Returns:
        Paginated list of prompt records
    """
    try:
        if project_name:
            prompts = await repository.find_by_project(project_name, limit, offset)
        else:
            prompts = await repository.find_all(limit, offset)
        
        # This is a simplified implementation - in a real application, 
        # you would also return the total count of records
        return PromptListResponse(
            items=prompts,
            total=len(prompts),  # This should be the total count from the repository
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    repository: PromptRepository = Depends(get_prompt_repository),
):
    """
    Get a prompt record by ID.
    
    Args:
        prompt_id: Prompt record ID
        repository: Prompt repository
        
    Returns:
        Prompt record
    """
    try:
        prompt = await repository.get_optional(prompt_id)
        
        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        return prompt
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/prompts/{prompt_id}/labels", status_code=204)
async def add_label(
    prompt_id: UUID,
    label: LabelCreate,
    repository: PromptRepository = Depends(get_prompt_repository),
):
    """
    Add a label to a prompt record.
    
    Args:
        prompt_id: Prompt record ID
        label: Label to add
        repository: Prompt repository
    """
    try:
        success = await repository.add_label(prompt_id, label.label)
        
        if not success:
            raise HTTPException(status_code=404, detail="Prompt not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/prompts/ui/list", response_class=HTMLResponse)
async def list_prompts_ui(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    project_name: Optional[str] = None,
    repository: PromptRepository = Depends(get_prompt_repository),
    templates: Jinja2Templates = Depends(get_templates),
):
    """
    Render HTML for prompt list (for HTMX).
    
    Args:
        request: FastAPI request
        limit: Maximum number of records to return
        offset: Number of records to skip
        project_name: Filter by project name
        repository: Prompt repository
        templates: Jinja2 templates
        
    Returns:
        HTML response
    """
    try:
        if project_name:
            prompts = await repository.find_by_project(project_name, limit, offset)
        else:
            prompts = await repository.find_all(limit, offset)
        
        # Prepare data for template
        prompt_data = []
        for prompt in prompts:
            # Truncate prompt and response for list view
            truncated_prompt = prompt.prompt_text[:100] + "..." if len(prompt.prompt_text) > 100 else prompt.prompt_text
            truncated_response = prompt.response_text[:100] + "..." if len(prompt.response_text) > 100 else prompt.response_text
            
            prompt_data.append({
                "id": prompt.id,
                "project_name": prompt.project_name,
                "formatted_timestamp": prompt.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "terminal_type": prompt.terminal_type,
                "labels": prompt.labels,
                "truncated_prompt": truncated_prompt,
                "truncated_response": truncated_response,
            })
        
        return templates.TemplateResponse(
            "partials/prompt_list.html",
            {
                "request": request,
                "prompts": prompt_data,
                "limit": limit,
                "offset": offset,
                "has_next": len(prompts) == limit,
                "has_prev": offset > 0,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/prompts/ui/{prompt_id}", response_class=HTMLResponse)
async def get_prompt_ui(
    request: Request,
    prompt_id: UUID,
    repository: PromptRepository = Depends(get_prompt_repository),
    templates: Jinja2Templates = Depends(get_templates),
):
    """
    Render HTML for prompt detail (for HTMX).
    
    Args:
        request: FastAPI request
        prompt_id: Prompt record ID
        repository: Prompt repository
        templates: Jinja2 templates
        
    Returns:
        HTML response
    """
    try:
        prompt = await repository.get_optional(prompt_id)
        
        if prompt is None:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        # Prepare data for template
        prompt_data = {
            "id": prompt.id,
            "project_name": prompt.project_name,
            "project_goal": prompt.project_goal,
            "formatted_timestamp": prompt.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "terminal_type": prompt.terminal_type,
            "prompt_text": prompt.prompt_text,
            "response_text": prompt.response_text,
            "labels": prompt.labels,
        }
        
        return templates.TemplateResponse(
            "partials/prompt_detail.html",
            {
                "request": request,
                "prompt": prompt_data,
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))