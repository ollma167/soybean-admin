from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models import Template, TemplateCombo, ComboItem
from app.schemas import TemplateCreate, TemplateUpdate
from app.utils.redis_client import cache_get, cache_set, cache_delete, cache_key
import structlog

logger = structlog.get_logger()


class TemplateService:
    """Template service"""
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[Template]:
        """Get all templates"""
        query = db.query(Template)
        if is_active is not None:
            query = query.filter(Template.is_active == is_active)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_id(db: Session, template_id: int, use_cache: bool = True) -> Optional[Template]:
        """Get template by ID"""
        # Try cache first
        if use_cache:
            cache_k = cache_key("template", template_id)
            cached = cache_get(cache_k)
            if cached:
                logger.info("Template cache hit", template_id=template_id)
                return cached
        
        template = db.query(Template).filter(Template.id == template_id).first()
        
        # Cache the result
        if template and use_cache:
            cache_k = cache_key("template", template_id)
            cache_set(cache_k, template.to_dict())
        
        return template
    
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Template]:
        """Get template by name"""
        return db.query(Template).filter(Template.name == name).first()
    
    @staticmethod
    def create(db: Session, template_data: TemplateCreate) -> Template:
        """Create new template"""
        # Create template
        template = Template(
            name=template_data.name,
            description=template_data.description,
            is_active=template_data.is_active
        )
        db.add(template)
        db.flush()
        
        # Create combos and items
        for combo_data in template_data.combos:
            combo = TemplateCombo(
                template_id=template.id,
                prefix=combo_data.prefix,
                sort_order=combo_data.sort_order
            )
            db.add(combo)
            db.flush()
            
            for item_data in combo_data.items:
                item = ComboItem(
                    combo_id=combo.id,
                    product_code=item_data.product_code,
                    quantity=item_data.quantity,
                    sale_price=item_data.sale_price,
                    base_price=item_data.base_price,
                    cost_price=item_data.cost_price
                )
                db.add(item)
        
        db.commit()
        db.refresh(template)
        
        logger.info("Template created", template_id=template.id, name=template.name)
        return template
    
    @staticmethod
    def update(db: Session, template_id: int, template_data: TemplateUpdate) -> Optional[Template]:
        """Update template"""
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return None
        
        # Update basic fields
        if template_data.name is not None:
            template.name = template_data.name
        if template_data.description is not None:
            template.description = template_data.description
        if template_data.is_active is not None:
            template.is_active = template_data.is_active
        
        # Update combos if provided
        if template_data.combos is not None:
            # Delete existing combos (cascade will delete items)
            db.query(TemplateCombo).filter(TemplateCombo.template_id == template_id).delete()
            
            # Create new combos
            for combo_data in template_data.combos:
                combo = TemplateCombo(
                    template_id=template.id,
                    prefix=combo_data.prefix,
                    sort_order=combo_data.sort_order
                )
                db.add(combo)
                db.flush()
                
                for item_data in combo_data.items:
                    item = ComboItem(
                        combo_id=combo.id,
                        product_code=item_data.product_code,
                        quantity=item_data.quantity,
                        sale_price=item_data.sale_price,
                        base_price=item_data.base_price,
                        cost_price=item_data.cost_price
                    )
                    db.add(item)
        
        db.commit()
        db.refresh(template)
        
        # Invalidate cache
        cache_k = cache_key("template", template_id)
        cache_delete(cache_k)
        
        logger.info("Template updated", template_id=template.id)
        return template
    
    @staticmethod
    def delete(db: Session, template_id: int) -> bool:
        """Delete template"""
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return False
        
        db.delete(template)
        db.commit()
        
        # Invalidate cache
        cache_k = cache_key("template", template_id)
        cache_delete(cache_k)
        
        logger.info("Template deleted", template_id=template_id)
        return True
    
    @staticmethod
    def count(db: Session, is_active: Optional[bool] = None) -> int:
        """Count templates"""
        query = db.query(Template)
        if is_active is not None:
            query = query.filter(Template.is_active == is_active)
        return query.count()
    
    @staticmethod
    def search(db: Session, keyword: str, skip: int = 0, limit: int = 100) -> List[Template]:
        """Search templates by keyword"""
        return db.query(Template).filter(
            Template.name.like(f"%{keyword}%")
        ).offset(skip).limit(limit).all()
