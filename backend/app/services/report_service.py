from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Dict, List
from datetime import date, timedelta
from app.models.product import ProductRecord
from app.models.expense import Expense
from app.models.recipe import Recipe
from decimal import Decimal


async def generate_expense_report(
    user_id: int,
    start_date: date,
    end_date: date,
    category: str = "all",
    granularity: str = "daily",
    db: Session = None
) -> Dict:
    """生成支出报告"""
    total_expense = Decimal("0.00")
    time_series = []

    current_date = start_date
    while current_date <= end_date:
        # 商品支出
        if category in ["all", "food"]:
            food_total = db.query(
                func.sum(ProductRecord.price).label('total')
            ).filter(
                ProductRecord.user_id == user_id,
                func.date(ProductRecord.recorded_at) == current_date
            ).first()
            food_amount = food_total.total if food_total.total else Decimal("0.00")
            total_expense += food_amount
        else:
            food_amount = Decimal("0.00")

        # 其他费用
        if category in ["all", "transport"]:
            transport_total = db.query(
                func.sum(Expense.amount).label('total')
            ).filter(
                Expense.user_id == user_id,
                Expense.type == "transport",
                Expense.date == current_date
            ).first()
            transport_amount = transport_total.total if transport_total.total else Decimal("0.00")
            total_expense += transport_amount
        else:
            transport_amount = Decimal("0.00")

        # 水电气费用
        if category in ["all", "utility"]:
            utility_total = db.query(
                func.sum(Expense.amount).label('total')
            ).filter(
                Expense.user_id == user_id,
                Expense.date == current_date,
                Expense.type.in_(["water", "gas", "electricity"])
            ).first()
            utility_amount = utility_total.total if utility_total.total else Decimal("0.00")
            total_expense += utility_amount
        else:
            utility_amount = Decimal("0.00")

        time_series.append({
            "date": current_date.isoformat(),
            "amount": float(total_expense)
        })

        current_date += timedelta(days=1)

    category_breakdown = {"food": food_amount, "transport": transport_amount, "utility": utility_amount}

    return {
        "total_expense": total_expense,
        "currency": "CNY",
        "category_breakdown": category_breakdown,
        "time_series": time_series
    }


async def generate_price_trend(
    user_id: int,
    product_name: str,
    db: Session = None
) -> Dict:
    """生成价格趋势"""
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.product_name.contains(product_name)
    ).order_by(ProductRecord.recorded_at.asc()).all()

    time_series = []
    for record in records:
        time_series.append({
            "date": record.recorded_at.strftime("%Y-%m-%d"),
            "price": float(record.price),
            "currency": record.currency
        })

    return {
        "product_name": product_name,
        "time_series": time_series
    }
