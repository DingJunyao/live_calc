"""
每日饮食推荐模型

存储每位用户每天每餐的菜谱推荐记录。
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DailyRecommendation(Base):
    __tablename__ = "daily_recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "date", "meal_type", name="uq_user_date_meal"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)  # breakfast / lunch / dinner
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="daily_recommendations")
    recipe = relationship("Recipe")
