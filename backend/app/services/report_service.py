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

    # 初始化各类别的总计
    total_food = Decimal("0.00")
    total_transport = Decimal("0.00")
    total_utility = Decimal("0.00")

    current_date = start_date
    while current_date <= end_date:
        daily_food = Decimal("0.00")
        daily_transport = Decimal("0.00")
        daily_utility = Decimal("0.00")

        # 商品支出（只计算购买记录，不计算单纯的价格记录）
        if category in ["all", "food"]:
            food_total = db.query(
                func.sum(ProductRecord.price).label('total')
            ).filter(
                ProductRecord.user_id == user_id,
                ProductRecord.record_type == "purchase",  # 这个SB过滤条件确保只计算购买记录
                func.date(ProductRecord.recorded_at) == current_date
            ).first()
            daily_food = food_total.total if food_total and food_total.total else Decimal("0.00")
            total_food += daily_food

        # 其他费用
        if category in ["all", "transport"]:
            transport_total = db.query(
                func.sum(Expense.amount).label('total')
            ).filter(
                Expense.user_id == user_id,
                Expense.type == "transport",
                Expense.date == current_date
            ).first()
            daily_transport = transport_total.total if transport_total and transport_total.total else Decimal("0.00")
            total_transport += daily_transport

        # 水电气费用
        if category in ["all", "utility"]:
            utility_total = db.query(
                func.sum(Expense.amount).label('total')
            ).filter(
                Expense.user_id == user_id,
                Expense.date == current_date,
                Expense.type.in_(["water", "gas", "electricity"])
            ).first()
            daily_utility = utility_total.total if utility_total and utility_total.total else Decimal("0.00")
            total_utility += daily_utility

        # 计算当天总支出
        daily_total = daily_food + daily_transport + daily_utility
        total_expense += daily_total

        time_series.append({
            "date": current_date.isoformat(),
            "amount": float(daily_total)
        })

        current_date += timedelta(days=1)

    category_breakdown = {"food": float(total_food), "transport": float(total_transport), "utility": float(total_utility)}

    return {
        "total_expense": float(total_expense),
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
