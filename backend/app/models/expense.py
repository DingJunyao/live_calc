from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Enum as PyEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExpenseType(PyEnum):
    WATER = "water"
    GAS = "gas"
    ELECTRICITY = "electricity"
    TRANSPORT = "transport"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20))
    date = Column(Date, nullable=False)
    notes = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="expenses")
