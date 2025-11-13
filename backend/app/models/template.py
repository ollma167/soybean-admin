from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Template(Base):
    """Template model"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    combos = relationship("TemplateCombo", back_populates="template", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "combos": [combo.to_dict() for combo in self.combos] if self.combos else []
        }


class TemplateCombo(Base):
    """Template combo configuration"""
    __tablename__ = "template_combos"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False, index=True)
    prefix = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    template = relationship("Template", back_populates="combos")
    items = relationship("ComboItem", back_populates="combo", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "prefix": self.prefix,
            "sort_order": self.sort_order,
            "items": [item.to_dict() for item in self.items] if self.items else []
        }


class ComboItem(Base):
    """Combo item detail"""
    __tablename__ = "combo_items"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("template_combos.id", ondelete="CASCADE"), nullable=False, index=True)
    product_code = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, default=1)
    sale_price = Column(DECIMAL(10, 4), default=1.0)
    base_price = Column(DECIMAL(10, 4), default=1.0)
    cost_price = Column(DECIMAL(10, 4), default=1.0)
    
    # Relationships
    combo = relationship("TemplateCombo", back_populates="items")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "combo_id": self.combo_id,
            "product_code": self.product_code,
            "quantity": self.quantity,
            "sale_price": float(self.sale_price),
            "base_price": float(self.base_price),
            "cost_price": float(self.cost_price)
        }


class OperationLog(Base):
    """Operation log model"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
