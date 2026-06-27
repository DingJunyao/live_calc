"""P2 共享数据测试。"""
from conftest import TestingSessionLocal, engine
from app.models.price_summary import ProductMerchantPriceSummary
from app.core.database import Base


def test_summary_has_no_user_or_record_type_columns():
    """汇总表去标识：不含 user_id / record_type。"""
    cols = {c.name for c in ProductMerchantPriceSummary.__table__.columns}
    assert "user_id" not in cols
    assert "record_type" not in cols


def test_recompute_summary_aggregates_price_records():
    """recompute_summary 把 ProductRecord（PRICE+PURCHASE）聚合为单价 ¥/斤 写入汇总表。"""
    from app.services.price_aggregator import recompute_summary
    from app.models.product import ProductRecord

    # 确保表存在（conftest 导入时已 create_all，这里幂等再保一次）
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        # 清理 + 构造 3 条 ProductRecord（2 PRICE + 1 PURCHASE，同 product×merchant）
        db.query(ProductRecord).delete()
        db.query(ProductMerchantPriceSummary).delete()
        db.commit()
        # 单价 = price × 500 / standard_quantity
        #  - price=10, std=500 → 10 ¥/斤（最近一条，records 按 recorded_at desc 取首）
        #  - price=20, std=1000 → 10 ¥/斤
        #  - price=30, std=250 → 60 ¥/斤
        for price, std, rt in [(10.0, 500, "price"), (20.0, 1000, "price"), (30.0, 250, "purchase")]:
            db.add(ProductRecord(
                user_id=1, product_id=10, product_name="测试", merchant_id=5,
                price=price, currency="CNY", original_quantity=1, original_unit_id=1,
                standard_quantity=std, standard_unit_id=1, record_type=rt,
            ))
        db.commit()
        recompute_summary(db, product_id=10, merchant_id=5)
        db.commit()
        row = db.query(ProductMerchantPriceSummary).filter_by(product_id=10, merchant_id=5).first()
        assert row is not None
        # 3 条都参与了聚合（PRICE + PURCHASE 一视同仁）
        assert row.sample_count == 3
        # 全部归一化为 ¥/斤 单价：min=10, max=60, avg=(10+10+60)/3=26.67
        assert row.min_price is not None and float(row.min_price) == 10.0
        assert row.max_price is not None and float(row.max_price) == 60.0
        assert row.avg_price_30d is not None and abs(float(row.avg_price_30d) - 80.0 / 3) < 0.01
        # recent_price：按 recorded_at desc 取首条有效单价；3 条同时间戳时取 ORM 返回首条
        assert row.recent_price is not None
    finally:
        db.query(ProductRecord).delete()
        db.query(ProductMerchantPriceSummary).delete()
        db.commit()
        db.close()
