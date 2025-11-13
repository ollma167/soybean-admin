#!/usr/bin/env python3
"""
Migrate templates from JSON file to MySQL database
"""
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Template, TemplateCombo, ComboItem
from app.config import settings


def load_json_templates(json_file: str):
    """Load templates from JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and "templates" in data:
        return data["templates"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Invalid JSON format")


def migrate_templates(json_file: str, database_url: str = None):
    """Migrate templates from JSON to database"""
    # Use provided database URL or default from settings
    db_url = database_url or settings.database_url
    
    print(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)
    
    # Create tables if they don't exist
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Load JSON templates
        print(f"Loading templates from: {json_file}")
        json_templates = load_json_templates(json_file)
        print(f"Found {len(json_templates)} templates")
        
        # Migrate each template
        migrated_count = 0
        skipped_count = 0
        
        for json_template in json_templates:
            template_name = json_template.get("name", "")
            
            # Check if template already exists
            existing = db.query(Template).filter(Template.name == template_name).first()
            if existing:
                print(f"Skipping existing template: {template_name}")
                skipped_count += 1
                continue
            
            print(f"Migrating template: {template_name}")
            
            # Create template
            template = Template(
                name=template_name,
                description=json_template.get("description", ""),
                is_active=True
            )
            db.add(template)
            db.flush()
            
            # Create combos
            combos = json_template.get("combos", [])
            for idx, combo_data in enumerate(combos):
                combo = TemplateCombo(
                    template_id=template.id,
                    prefix=combo_data.get("prefix", ""),
                    sort_order=idx
                )
                db.add(combo)
                db.flush()
                
                # Create items
                items = combo_data.get("items", [])
                for item_data in items:
                    # Handle both Chinese and English field names
                    product_code = item_data.get("商品编码", item_data.get("product_code", ""))
                    quantity = item_data.get("数量", item_data.get("quantity", 1))
                    sale_price = item_data.get("应占售价", item_data.get("sale_price", 1.0))
                    base_price = item_data.get("基本售价", item_data.get("base_price", 1.0))
                    cost_price = item_data.get("组合成本价", item_data.get("cost_price", 1.0))
                    
                    item = ComboItem(
                        combo_id=combo.id,
                        product_code=product_code,
                        quantity=int(quantity),
                        sale_price=float(sale_price),
                        base_price=float(base_price),
                        cost_price=float(cost_price)
                    )
                    db.add(item)
            
            migrated_count += 1
        
        # Commit all changes
        db.commit()
        print(f"\nMigration completed!")
        print(f"Migrated: {migrated_count} templates")
        print(f"Skipped: {skipped_count} templates (already exist)")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate templates from JSON to MySQL")
    parser.add_argument("json_file", help="Path to JSON templates file")
    parser.add_argument("--database-url", help="Database URL (optional, uses config if not provided)")
    
    args = parser.parse_args()
    
    migrate_templates(args.json_file, args.database_url)
