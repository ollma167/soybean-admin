import re
from typing import List, Dict, Any, Tuple
from decimal import Decimal


class ComboGenerator:
    """Combo generator utility - migrated from combo_tool.py"""
    
    TEMPLATE_COLUMNS = [
        '组合商品编码', '组合商品标签', '组合款式编码', '组合商品名称', '组合商品简称', '组合商品实体编码',
        '虚拟分类', '组合颜色规格', '禁止库存同步', '商品编码', '数量', '应占售价', '基本售价', '组合成本价', '图片', '品牌'
    ]
    
    @staticmethod
    def _num(val, default):
        """Convert value to number"""
        if val is None or str(val).strip() == "":
            return default
        try:
            f = float(str(val))
            i = int(f)
            return i if abs(f - i) < 1e-9 else f
        except:
            return default
    
    @staticmethod
    def _apply_rules_on_body(body: str, rules: List[Tuple[str, str]], use_regex: bool, case_sensitive: bool) -> str:
        """Apply simplification rules on string body"""
        flags = 0 if case_sensitive else re.IGNORECASE
        for old, new in rules:
            if old == "":
                continue
            if use_regex:
                try:
                    body = re.sub(old, new, body, flags=flags)
                except re.error:
                    body = body.replace(old, new) if case_sensitive else re.compile(
                        re.escape(old), re.IGNORECASE
                    ).sub(new, body)
            else:
                body = body.replace(old, new) if case_sensitive else re.compile(
                    re.escape(old), re.IGNORECASE
                ).sub(new, body)
        return body
    
    @staticmethod
    def apply_code_simplify(
        original: str,
        prefix: str,
        rules: List[Tuple[str, str]],
        use_regex: bool,
        case_sensitive: bool
    ) -> str:
        """Apply code simplification rules"""
        head, body = (prefix, original[len(prefix):]) if original.startswith(prefix) else ("", original)
        body = ComboGenerator._apply_rules_on_body(body, rules, use_regex, case_sensitive)
        return f"{head}{body}"
    
    @staticmethod
    def apply_name_simplify(
        name: str,
        prefix: str,
        rules: List[Tuple[str, str]],
        use_regex: bool,
        case_sensitive: bool
    ) -> str:
        """Apply name simplification rules"""
        head, tail = (prefix, name[len(prefix):]) if name.startswith(prefix) else ("", name)
        tail = ComboGenerator._apply_rules_on_body(tail, rules, use_regex, case_sensitive)
        return f"{head}{tail}"
    
    @staticmethod
    def build_rows(
        main_products: List[Dict[str, Any]],
        combos: List[Tuple[str, List[Dict[str, Any]]]],
        simplify_rules: List[Tuple[str, str]] = None,
        use_regex: bool = False,
        case_sensitive: bool = True,
        apply_to_name: bool = False
    ) -> List[Dict[str, Any]]:
        """Build combo rows from main products and combos"""
        rows = []
        simplify_rules = simplify_rules or []
        
        for prefix, items in combos:
            for main_prod in main_products:
                code = str(main_prod.get("主商品编码", ""))
                spec = str(main_prod.get("主商品组合颜色规格", ""))
                qty = ComboGenerator._num(main_prod.get("数量"), 1)
                price1 = ComboGenerator._num(main_prod.get("应占售价"), 1.0)
                price2 = ComboGenerator._num(main_prod.get("基本售价"), 1.0)
                cost = ComboGenerator._num(main_prod.get("成本价"), 1.0)
                
                if not code or not spec:
                    continue
                
                combo_code_raw = f"{prefix}{code}"
                combo_code_final = ComboGenerator.apply_code_simplify(
                    combo_code_raw, prefix, simplify_rules, use_regex, case_sensitive
                )
                combo_name_raw = f"{prefix}{spec}"
                combo_name_final = ComboGenerator.apply_name_simplify(
                    combo_name_raw, prefix, simplify_rules, use_regex, case_sensitive
                ) if apply_to_name else combo_name_raw
                
                # Calculate totals from sub-items
                total_sub_price1 = sum(
                    ComboGenerator._num(it.get('应占售价', 1.0), 1.0) * ComboGenerator._num(it.get('数量', 1), 1)
                    for it in items
                )
                total_sub_price2 = sum(
                    ComboGenerator._num(it.get('基本售价', 1.0), 1.0) * ComboGenerator._num(it.get('数量', 1), 1)
                    for it in items
                )
                total_sub_cost = sum(
                    ComboGenerator._num(it.get('组合成本价', 1.0), 1.0) * ComboGenerator._num(it.get('数量', 1), 1)
                    for it in items
                )
                
                # Main combo row
                main_row = {col: "" for col in ComboGenerator.TEMPLATE_COLUMNS}
                main_row.update({
                    '组合商品编码': combo_code_final,
                    '组合商品名称': combo_name_final,
                    '组合颜色规格': spec,
                    '商品编码': code,
                    '数量': qty,
                    '应占售价': price1 + total_sub_price1,
                    '基本售价': price2 + total_sub_price2,
                    '组合成本价': cost + total_sub_cost
                })
                rows.append(main_row)
                
                # Sub-item rows
                for it in items:
                    sub_row = {col: "" for col in ComboGenerator.TEMPLATE_COLUMNS}
                    sub_row.update({
                        '商品编码': it.get('商品编码', ''),
                        '数量': ComboGenerator._num(it.get('数量', 1), 1),
                        '应占售价': ComboGenerator._num(it.get('应占售价', 1.0), 1.0),
                        '基本售价': ComboGenerator._num(it.get('基本售价', 1.0), 1.0),
                        '组合成本价': ComboGenerator._num(it.get('组合成本价', 1.0), 1.0)
                    })
                    rows.append(sub_row)
        
        return rows
    
    @staticmethod
    def convert_db_template_to_combo_format(template_data: Dict[str, Any]) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Convert database template format to combo format"""
        combos = []
        for combo in template_data.get('combos', []):
            prefix = combo.get('prefix', '')
            items = []
            for item in combo.get('items', []):
                items.append({
                    '商品编码': item.get('product_code', ''),
                    '数量': item.get('quantity', 1),
                    '应占售价': float(item.get('sale_price', 1.0)),
                    '基本售价': float(item.get('base_price', 1.0)),
                    '组合成本价': float(item.get('cost_price', 1.0))
                })
            combos.append((prefix, items))
        return combos
