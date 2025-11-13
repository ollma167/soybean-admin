from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.services import TemplateService
from app.schemas import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    Response,
    PaginatedResponse
)
from app.models import Template
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TemplateListResponse])
async def list_templates(
    skip: int = Query(0, ge=0, description="Skip records"),
    limit: int = Query(100, ge=1, le=1000, description="Limit records"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    db: Session = Depends(get_db)
):
    """List all templates"""
    try:
        if keyword:
            templates = TemplateService.search(db, keyword, skip, limit)
            total = len(templates)
        else:
            templates = TemplateService.get_all(db, skip, limit, is_active)
            total = TemplateService.count(db, is_active)
        
        # Convert to list response format
        template_list = []
        for template in templates:
            template_list.append(TemplateListResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                is_active=template.is_active,
                created_at=template.created_at,
                updated_at=template.updated_at,
                combo_count=len(template.combos) if template.combos else 0
            ))
        
        return PaginatedResponse(
            code=200,
            message="Success",
            data=template_list,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=Response[TemplateResponse])
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get template by ID"""
    try:
        template = TemplateService.get_by_id(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return Response(
            code=200,
            message="Success",
            data=TemplateResponse.model_validate(template)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}", template_id=template_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Response[TemplateResponse], status_code=201)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db)
):
    """Create new template"""
    try:
        # Check if template name already exists
        existing = TemplateService.get_by_name(db, template_data.name)
        if existing:
            raise HTTPException(status_code=400, detail="Template name already exists")
        
        template = TemplateService.create(db, template_data)
        
        return Response(
            code=201,
            message="Template created successfully",
            data=TemplateResponse.model_validate(template)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=Response[TemplateResponse])
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update template"""
    try:
        # Check if new name conflicts with another template
        if template_data.name:
            existing = TemplateService.get_by_name(db, template_data.name)
            if existing and existing.id != template_id:
                raise HTTPException(status_code=400, detail="Template name already exists")
        
        template = TemplateService.update(db, template_id, template_data)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return Response(
            code=200,
            message="Template updated successfully",
            data=TemplateResponse.model_validate(template)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}", template_id=template_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}", response_model=Response)
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete template"""
    try:
        success = TemplateService.delete(db, template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return Response(
            code=200,
            message="Template deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}", template_id=template_id)
        raise HTTPException(status_code=500, detail=str(e))
