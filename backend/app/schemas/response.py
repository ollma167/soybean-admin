from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Standard API response"""
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "Success",
                "data": {}
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response"""
    code: int = 200
    message: str = "Success"
    data: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "Success",
                "data": [],
                "total": 0,
                "page": 1,
                "page_size": 10
            }
        }


class ErrorResponse(BaseModel):
    """Error response"""
    code: int
    message: str
    detail: Optional[Any] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 400,
                "message": "Bad Request",
                "detail": "Invalid input data"
            }
        }
