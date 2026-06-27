"""价格聚合：把 ProductRecord（PRICE + PURCHASE）聚合到去标识汇总表。

汇总表不含 user_id / record_type（P2 共享转型核心：跨用户公开聚合，去标识）。
写入时（products.py create_product_record）增量调用 recompute_summary 重算对应
product×merchant 的统计；本模块只读写 ProductMerchantPriceSummary，绝不暴露用户身份。
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.product import ProductRecord
from app.models.price_summary import ProductMerchantPriceSummary


def recompute_summary(db: Session, *, product_id: int, merchant_id: Optional[int]) -> None:
    """重算指定 product×merchant 的汇总行。

    聚合该 product×merchant 下所有 is_active 的 ProductRecord（PRICE + PURCHASE 一视同仁），
    不区分 user_id / record_type（去标识 + 去记录类型）。结果 upsert 进汇总表。
    merchant_id 为 None 时聚合该 product 的所有记录（无商家维度）。

    注意：汇总存的是「单位归一化单价 ¥/斤」（price × 500 / standard_quantity），
    与 nutrition.py sparkline 算法一致，确保跨单位可比。
    standard_quantity 为 0/None 时按 500（即 1 斤）兜底。
    latest-price 端点不读此汇总表，仅供未来趋势/K 线等使用。
    """
    # 拉取原始记录，在 Python 端归一化为 ¥/斤 后再聚合
    # （pure-SQL 难以表达「standard_quantity 为 0/None 时取 500」的兜底）
    q = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.is_active == True,  # noqa: E712
    )
    if merchant_id is not None:
        q = q.filter(ProductRecord.merchant_id == merchant_id)
    records = q.order_by(ProductRecord.recorded_at.desc()).all()

    unit_prices: list[float] = []
    recent_unit_price: Optional[float] = None
    for idx, r in enumerate(records):
        if r.price is None:
            continue
        std_qty = float(r.standard_quantity) if r.standard_quantity and float(r.standard_quantity) > 0 else 500.0
        unit_price = float(r.price) * 500.0 / std_qty
        unit_prices.append(unit_price)
        # records 已按 recorded_at desc 排序，第一条有效单价即为最近价
        if idx == 0:
            recent_unit_price = unit_price

    if unit_prices:
        cnt = len(unit_prices)
        mn = min(unit_prices)
        mx = max(unit_prices)
        avg = sum(unit_prices) / cnt
    else:
        cnt = 0
        mn = mx = avg = None

    existing = db.query(ProductMerchantPriceSummary).filter_by(
        product_id=product_id, merchant_id=merchant_id
    ).first()
    if existing is None:
        existing = ProductMerchantPriceSummary(product_id=product_id, merchant_id=merchant_id)
        db.add(existing)
    existing.sample_count = cnt
    existing.min_price = mn
    existing.max_price = mx
    existing.avg_price_30d = avg
    existing.recent_price = recent_unit_price
    existing.last_updated_at = datetime.utcnow()
    db.flush()
