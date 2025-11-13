from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.services.template_service import TemplateService
from app.utils.combo_generator import ComboGenerator
from app.schemas.template import GenerateComboRequest
from decimal import Decimal
import structlog

logger = structlog.get_logger()


class ComboService:
    """Combo generation service"""
    
    @staticmethod
    def generate_combos(db: Session, request: GenerateComboRequest) -> Dict[str, Any]:
        """Generate combo products"""
        # Get template
        template = TemplateService.get_by_id(db, request.template_id)
        if not template:
            raise ValueError(f"Template {request.template_id} not found")
        
        # Validate input lengths
        if len(request.main_product_codes) != len(request.main_product_specs):
            raise ValueError("Main product codes and specs must have the same length")
        
        # Prepare main products data
        main_products = []
        for i, code in enumerate(request.main_product_codes):
            main_product = {
                "主商品编码": code,
                "主商品组合颜色规格": request.main_product_specs[i],
                "数量": request.main_product_quantities[i] if request.main_product_quantities and i < len(request.main_product_quantities) else 1,
                "应占售价": float(request.main_product_sale_prices[i]) if request.main_product_sale_prices and i < len(request.main_product_sale_prices) else 1.0,
                "基本售价": float(request.main_product_base_prices[i]) if request.main_product_base_prices and i < len(request.main_product_base_prices) else 1.0,
                "成本价": float(request.main_product_cost_prices[i]) if request.main_product_cost_prices and i < len(request.main_product_cost_prices) else 1.0,
            }
            main_products.append(main_product)
        
        # Convert template to combo format
        template_dict = template.to_dict()
        combos = ComboGenerator.convert_db_template_to_combo_format(template_dict)
        
        # Prepare simplify rules
        simplify_rules = []
        if request.simplify_rules:
            for rule in request.simplify_rules:
                old = rule.get('old', '')
                new = rule.get('new', '')
                simplify_rules.append((old, new))
        
        # Generate combo rows
        rows = ComboGenerator.build_rows(
            main_products=main_products,
            combos=combos,
            simplify_rules=simplify_rules,
            use_regex=request.use_regex,
            case_sensitive=request.case_sensitive,
            apply_to_name=request.apply_to_name
        )
        
        logger.info(
            "Combo generation completed",
            template_id=request.template_id,
            main_products_count=len(main_products),
            rows_generated=len(rows)
        )
        
        return {
            "rows": rows,
            "total_count": len(rows),
            "template_name": template.name
        }
    
    @staticmethod
    def validate_template_data(template_data: Dict[str, Any]) -> bool:
        """Validate template data structure"""
        if not isinstance(template_data, dict):
            return False
        
        if 'name' not in template_data:
            return False
        
        if 'combos' in template_data:
            if not isinstance(template_data['combos'], list):
                return False
            
            for combo in template_data['combos']:
                if not isinstance(combo, dict):
                    return False
                if 'prefix' not in combo:
                    return False
                if 'items' in combo and not isinstance(combo['items'], list):
                    return False
        
        return True
