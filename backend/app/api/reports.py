from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.report import (
    ExpenseCreate,
    ExpenseResponse,
    ReportRequest,
    ExpenseReportResponse,
    PriceTrendResponse
)
from app.services.report_service import generate_expense_report, generate_price_trend
from app.models.expense import Expense

router = APIRouter()


@router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建费用记录"""
    try:
        db_expense = Expense(
            user_id=current_user.id,
            type=expense.type,
            amount=expense.amount,
            unit=expense.unit,
            date=expense.date,
            notes=expense.notes
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建费用记录失败: {str(e)}")


@router.get("/expenses", response_model=List[ExpenseResponse])
async def get_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取费用记录"""
    try:
        query = db.query(Expense).filter(Expense.user_id == current_user.id)

        if start_date:
            query = query.filter(Expense.date >= start_date)
        if end_date:
            query = query.filter(Expense.date <= end_date)

        expenses = query.order_by(Expense.date.desc()).all()
        return expenses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取费用记录失败: {str(e)}")


@router.get("/expense", response_model=ExpenseReportResponse)
async def get_expense_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    category: str = Query("all"),
    granularity: str = Query("daily"),
    timezone_offset: Optional[int] = Query(None, description="用户时区偏移（秒），东八区为 28800"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取支出报告（支持时区感知）

    Args:
        start_date: 开始日期（用户本地日期）
        end_date: 结束日期（用户本地日期）
        category: 类别筛选
        granularity: 粒度
        timezone_offset: 时区偏移（秒），如不提供则默认使用东八区
    """
    try:
        result = await generate_expense_report(
            current_user.id,
            start_date,
            end_date,
            category,
            granularity,
            db=db,
            user_timezone_offset=timezone_offset
        )
        return ExpenseReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")


@router.get("/price-trend", response_model=PriceTrendResponse)
async def get_price_trend(
    product_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取价格趋势"""
    try:
        result = await generate_price_trend(current_user.id, product_name, db=db)
        return PriceTrendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取价格趋势失败: {str(e)}")
