from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Dict, List, Optional
from datetime import date, timedelta, datetime
from app.models.product import ProductRecord
from app.models.expense import Expense
from app.models.recipe import Recipe
from app.utils.date_range_utils import local_date_range_to_utc_range
from decimal import Decimal


async def generate_expense_report(
    user_id: int,
    start_date: date,
    end_date: date,
    category: str = "all",
    granularity: str = "daily",
    db: Session = None,
    tz: str = "UTC"
) -> Dict:
    """生成支出报告（时区感知版本）

    Args:
        user_id: 用户ID
        start_date: 开始日期（用户本地日期）
        end_date: 结束日期（用户本地日期）
        category: 类别筛选
        granularity: 粒度
        db: 数据库会话
        tz: IANA 时区名，默认 UTC
    """
    total_expense = Decimal("0.00")
    time_series = []

    # 初始化各类别的总计
    total_food = Decimal("0.00")
    total_transport = Decimal("0.00")
    total_utility = Decimal("0.00")

    # 商品支出的范围查询在下方逐本地日循环中进行（时区感知），此处无需整体范围预查询。

    # 其他费用使用本地日期（Expense.date存储的是本地日期）
    current_date = start_date
    while current_date <= end_date:
        daily_food = Decimal("0.00")
        daily_transport = Decimal("0.00")
        daily_utility = Decimal("0.00")

        # 商品支出 - 从预查询的结果中匹配
        if category in ["all", "food"]:
            # 将当前本地日期转换为UTC日期范围
            day_utc_start, day_utc_end = local_date_range_to_utc_range(current_date, current_date, tz)

            # 查询当天的商品支出
            food_total = db.query(
                func.sum(ProductRecord.price).label('total')
            ).filter(
                ProductRecord.user_id == user_id,
                ProductRecord.record_type == "purchase",
                ProductRecord.recorded_at >= day_utc_start,
                ProductRecord.recorded_at <= day_utc_end
            ).first()
            daily_food = food_total.total if food_total and food_total.total else Decimal("0.00")
            total_food += daily_food

        # 其他费用（Expense.date存储的是本地日期，直接比较）
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


