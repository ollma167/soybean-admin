from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class ComboItemBase(BaseModel):
    """Base combo item schema"""
    product_code: str = Field(..., description="Product code", max_length=255)
    quantity: int = Field(default=1, ge=1, description="Quantity")
    sale_price: Decimal = Field(default=Decimal("1.0"), ge=0, description="Sale price")
    base_price: Decimal = Field(default=Decimal("1.0"), ge=0, description="Base price")
    cost_price: Decimal = Field(default=Decimal("1.0"), ge=0, description="Cost price")


class ComboItemCreate(ComboItemBase):
    """Create combo item schema"""
    pass


class ComboItemResponse(ComboItemBase):
    """Combo item response schema"""
    id: int
    combo_id: int
    
    model_config = ConfigDict(from_attributes=True)


class TemplateComboBase(BaseModel):
    """Base template combo schema"""
    prefix: str = Field(..., description="Combo prefix", max_length=100)
    sort_order: int = Field(default=0, description="Sort order")


class TemplateComboCreate(TemplateComboBase):
    """Create template combo schema"""
    items: List[ComboItemCreate] = Field(default_factory=list, description="Combo items")


class TemplateComboResponse(TemplateComboBase):
    """Template combo response schema"""
    id: int
    template_id: int
    items: List[ComboItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class TemplateBase(BaseModel):
    """Base template schema"""
    name: str = Field(..., description="Template name", max_length=255)
    description: Optional[str] = Field(None, description="Template description")
    is_active: bool = Field(default=True, description="Is active")


class TemplateCreate(TemplateBase):
    """Create template schema"""
    combos: List[TemplateComboCreate] = Field(default_factory=list, description="Template combos")


class TemplateUpdate(BaseModel):
    """Update template schema"""
    name: Optional[str] = Field(None, description="Template name", max_length=255)
    description: Optional[str] = Field(None, description="Template description")
    is_active: Optional[bool] = Field(None, description="Is active")
    combos: Optional[List[TemplateComboCreate]] = Field(None, description="Template combos")


class TemplateResponse(TemplateBase):
    """Template response schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    combos: List[TemplateComboResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Template list item response"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    combo_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class GenerateComboRequest(BaseModel):
    """Generate combo request schema"""
    template_id: int = Field(..., description="Template ID")
    main_product_codes: List[str] = Field(..., description="Main product codes")
    main_product_specs: List[str] = Field(..., description="Main product specifications")
    main_product_quantities: Optional[List[int]] = Field(None, description="Main product quantities")
    main_product_sale_prices: Optional[List[Decimal]] = Field(None, description="Main product sale prices")
    main_product_base_prices: Optional[List[Decimal]] = Field(None, description="Main product base prices")
    main_product_cost_prices: Optional[List[Decimal]] = Field(None, description="Main product cost prices")
    simplify_rules: Optional[List[dict]] = Field(None, description="Simplify rules")
    use_regex: bool = Field(default=False, description="Use regex in rules")
    case_sensitive: bool = Field(default=True, description="Case sensitive")
    apply_to_name: bool = Field(default=False, description="Apply rules to name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": 1,
                "main_product_codes": ["P001", "P002"],
                "main_product_specs": ["Blue-L", "Blue-M"],
                "main_product_quantities": [1, 1],
                "main_product_sale_prices": [100.0, 100.0],
                "main_product_base_prices": [90.0, 90.0],
                "main_product_cost_prices": [50.0, 50.0],
                "simplify_rules": [],
                "use_regex": False,
                "case_sensitive": True,
                "apply_to_name": False
            }
        }


class GenerateComboResponse(BaseModel):
    """Generate combo response schema"""
    rows: List[dict]
    total_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "rows": [],
                "total_count": 0
            }
        }
