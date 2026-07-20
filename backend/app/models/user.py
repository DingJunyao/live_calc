from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    token_version = Column(Integer, default=0, nullable=False)
    avatar = Column(String(500), nullable=True)  # storage key, e.g. avatars/uuid.png
    nickname = Column(String(50), nullable=True)  # display name, falls back to username when empty
    # 营养目标与预算
    daily_calorie_target = Column(Float, default=2000)
    daily_protein_target = Column(Float, default=60)
    daily_carb_target = Column(Float, default=300)
    daily_fat_target = Column(Float, default=65)
    daily_budget = Column(Float, nullable=True, default=None)
    # 用户默认单位偏好（NULL 时前端 fallback）
    default_energy_unit = Column(String(10), nullable=True)  # 'kcal' | 'kJ'
    default_mass_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    default_volume_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    default_price_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    # 所属行政区划
    region_id = Column(Integer, ForeignKey("administrative_regions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    product_records = relationship("ProductRecord", back_populates="user")
    merchants = relationship("Merchant", back_populates="user")
    user_places = relationship("UserPlace", back_populates="user", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="user", foreign_keys="Recipe.user_id")
    expenses = relationship("Expense", back_populates="user")
    created_invite_codes = relationship("InviteCode", back_populates="creator")
    ingredient_preferences = relationship("UserIngredientPreference", back_populates="user", foreign_keys="UserIngredientPreference.user_id")
    ingredient_blacklist = relationship("UserIngredientBlacklist", back_populates="user", foreign_keys="UserIngredientBlacklist.user_id")
    daily_recommendations = relationship("DailyRecommendation", back_populates="user")
