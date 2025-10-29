from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import ComboService
from app.schemas.template import GenerateComboRequest, GenerateComboResponse
from app.schemas.response import Response
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/generate", response_model=Response[GenerateComboResponse])
async def generate_combos(
    request: GenerateComboRequest,
    db: Session = Depends(get_db)
):
    """Generate combo products"""
    try:
        result = ComboService.generate_combos(db, request)
        
        return Response(
            code=200,
            message="Combos generated successfully",
            data=GenerateComboResponse(
                rows=result["rows"],
                total_count=result["total_count"]
            )
        )
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating combos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
