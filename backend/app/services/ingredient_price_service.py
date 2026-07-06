"""原料加权价格统一服务。

两层聚合：
  第一层（商品内）：每个商品当日有效记录的均价 → 该商品代表单价
  第二层（商品间）：按商品权重加权平均 Σ(pᵢ×wᵢ)/Σwᵢ

所有价格场景（原料最新价、菜谱成本、sparkline、报告）统一调用本服务。
记录查询复用 recipe_service._get_price_records_*，本服务只负责聚合。

权重读取优先级：用户覆盖(is_active) → Product.price_weight → 兜底 50。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.product_entity import Product
from app.models.user_product_weight_override import UserProductWeightOverride


def _product_unit_price(records: Sequence) -> Optional[Decimal]:
    """商品内均价：当日有效记录的 price / standard_quantity 平均。

    standard_quantity 为 None/0 时按 price 本身兜底（与 price_aggregator 一致）。
    """
    prices = []
    for r in records:
        if r.price is None:
            continue
        p = Decimal(str(r.price))
        sq = r.standard_quantity
        if sq is None or Decimal(str(sq)) == 0:
            prices.append(p)
        else:
            prices.append(p / Decimal(str(sq)))
    if not prices:
        return None
    return sum(prices) / Decimal(len(prices))


def _aggregate_weighted(product_records: dict) -> dict:
    """纯聚合：无 db 依赖。

    Args:
        product_records: { product_id: (records, weight, meta) }
            records: 该商品当日有效记录序列（ProductRecord 或伪对象）
            weight: int 0-100
            meta: {"product_id": int, "name": str, ...}（透传到 participants）

    Returns:
        {
          "unit_price": Optional[float],     # 加权单价（None = 无可用记录）
          "mode": "weighted"|"single"|"none",
          "participants": [{product_id, name, weight, unit_price, record_count, weight_source}],
          "excluded": [{product_id, name, reason}],  # reason ∈ {weight_zero, no_record}
        }
    """
    participants = []
    excluded = []
    for pid, entry in product_records.items():
        records, weight, meta = entry
        name = meta.get("name")
        if weight is None or weight <= 0:
            excluded.append({"product_id": pid, "name": name, "reason": "weight_zero"})
            continue
        intra = _product_unit_price(records)
        if intra is None:
            excluded.append({"product_id": pid, "name": name, "reason": "no_record"})
            continue
        participants.append({
            "product_id": pid,
            "name": name,
            "weight": int(weight),
            "unit_price": float(intra),
            "record_count": len([r for r in records if getattr(r, "price", None) is not None]),
            "weight_source": meta.get("weight_source", "global"),
        })

    if not participants:
        return {"unit_price": None, "mode": "none", "participants": [], "excluded": excluded}

    num = Decimal("0")
    den = Decimal("0")
    for p in participants:
        w = Decimal(p["weight"])
        num += Decimal(str(p["unit_price"])) * w
        den += w
    unit = float(num / den) if den > 0 else None
    mode = "single" if len(participants) == 1 else "weighted"
    return {"unit_price": unit, "mode": mode, "participants": participants, "excluded": excluded}


_DEFAULT_WEIGHT = 50


def _resolve_weight(db, *, user_id: Optional[int], product) -> int:
    """权重读取优先级：用户覆盖(is_active) → product.price_weight → 50。

    返回三元组里第一个非空：覆盖 > 全局 > 兜底。
    """
    if user_id is not None and product is not None:
        ov = db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == user_id,
            UserProductWeightOverride.product_id == product.id,
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).first()
        if ov is not None and ov.weight is not None:
            return int(ov.weight)
    gw = getattr(product, "price_weight", None)
    if gw is not None:
        return int(gw)
    return _DEFAULT_WEIGHT


def get_weighted_ingredient_price(
    db: Session,
    ingredient_id: int,
    *,
    as_of_date: datetime,
    user_id: Optional[int] = None,
    target_unit_abbr: Optional[str] = None,
    mode: str = "as_of",
) -> dict:
    """编排：查商品 → 查每个商品当日有效记录 → 查权重 → 调 _aggregate_weighted。

    mode:
      "as_of"  —— 成本语义：每商品按 _get_price_records_with_fallback(as_of_date) 取「当天/前向填充」
      "recent" —— 最新价语义：跨商品找最近有记录的那天，按商品分组（latest-price 用）

    无任何商品有记录时返回 unit_price=None，mode="none"，调用方走外部回退链。
    """
    # 延迟导入，避免循环依赖
    try:
        from app.services.recipe_service import _get_price_records_with_fallback
    except Exception:
        _get_price_records_with_fallback = None

    products = db.query(Product).filter(
        Product.ingredient_id == ingredient_id,
        Product.is_active == True,  # noqa: E712
    ).all()

    # 预取用户覆盖（一次查询）
    overrides = {}
    if user_id is not None and products:
        pid_list = [p.id for p in products]
        rows = db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == user_id,
            UserProductWeightOverride.product_id.in_(pid_list),
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).all()
        overrides = {r.product_id: r.weight for r in rows}

    # 收集每个商品的当日有效记录
    product_records = {}
    for p in products:
        if mode == "recent":
            records = _collect_recent_records(db, p.id, as_of_date)
        else:
            if _get_price_records_with_fallback is not None:
                records = _get_price_records_with_fallback(db, user_id, p.id, as_of_date)
            else:
                records = []
        # 权重 + source
        if p.id in overrides:
            w, src = overrides[p.id], "override"
        else:
            w = p.price_weight if p.price_weight is not None else _DEFAULT_WEIGHT
            src = "global"
        product_records[p.id] = (records, w, {"product_id": p.id, "name": p.name, "weight_source": src})

    result = _aggregate_weighted(product_records)
    result["target_unit"] = target_unit_abbr
    return result


def _collect_recent_records(db: Session, product_id: int, as_of_date: datetime) -> list:
    """latest-price 语义：该商品「最近有记录的那天」的全部记录。

    与 nutrition.get_ingredient_latest_price 的最近一天口径一致（去掉 24h 优先段，
    统一为「最近有记录日」以简化跨商品对齐）。
    """
    from app.models.product import ProductRecord
    latest = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.recorded_at <= as_of_date,
    ).order_by(ProductRecord.recorded_at.desc()).first()
    if not latest:
        return []
    d = latest.recorded_at.date()
    return db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.recorded_at >= datetime.combine(d, datetime.min.time()),
        ProductRecord.recorded_at <= datetime.combine(d, datetime.max.time()),
    ).all()


def resolve_direct_weighted_for_cost(db: Session, ingredient_id: int, *, user_id, as_of_date: datetime):
    """直接商品加权价（成本口径：元/standard_unit）。

    供菜谱成本计算用，取代 recipe_service 里「遍历商品取第一个有记录的」。
    返回 (unit_price_decimal, participants, std_unit_id) 或 None（无可用记录）。
    std_unit_id 取自首个参与商品的最近记录，供成本计算的后续单位转换段使用。
    """
    from app.models.product import ProductRecord
    w = get_weighted_ingredient_price(
        db, ingredient_id, as_of_date=as_of_date, user_id=user_id, mode="as_of",
    )
    if w["unit_price"] is None:
        return None
    pid = w["participants"][0]["product_id"]
    std_rec = db.query(ProductRecord).filter(
        ProductRecord.product_id == pid,
    ).order_by(ProductRecord.recorded_at.desc()).first()
    std_unit_id = std_rec.standard_unit_id if std_rec else None
    return Decimal(str(w["unit_price"])), w["participants"], std_unit_id
