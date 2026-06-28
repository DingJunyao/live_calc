"""商家合并执行器：把源商家的所有引用迁到目标商家，软停用源商家。

复用食材合并的 snapshot/revert 范式（见 executors/ingredient.py._apply_merge）：
apply 前对受影响行做完整快照——ProductRecord.merchant_id、user_merchant_favorites、
源商家 is_open+name；迁移 ProductRecord.merchant_id → target，删源收藏（目标已收藏的
去重由 UNIQUE(user_id, merchant_id) 约束保证），软停用源（is_open=False + 名称加
[已合并] 前缀）；revert 按快照逐项还原。

Merchant 无 is_active 字段，软停用语义与 executors/merchant.py（delete）一致：
is_open=False + 名称加后缀标记；但本执行器用 [已合并] 前缀与 delete 的 [已停用]
区分，避免回滚时混淆两种软停用语义。
"""
from typing import List

from fastapi import HTTPException

from app.services.proposals.base import ApplyResult, ProposalExecutor
from app.models.merchant import Merchant
from app.models.product import ProductRecord
from app.models.user_merchant_favorite import UserMerchantFavorite

_MERGED_PREFIX = "[已合并] "


class MerchantMergeExecutor(ProposalExecutor):
    entity_type = "merchant_merge"

    def validate(self, db, proposal) -> None:
        source_ids = proposal.payload.get("source_ids") or []
        target_id = proposal.payload.get("target_id")
        if not source_ids:
            raise HTTPException(status_code=400, detail="源商家列表不能为空")
        if target_id is None:
            raise HTTPException(status_code=400, detail="缺少目标商家")
        if target_id in source_ids:
            raise HTTPException(status_code=400, detail="目标商家不能同时是源商家")

    def preview(self, db, proposal) -> dict:
        source_ids: List[int] = list(proposal.payload["source_ids"])
        target_id = proposal.payload["target_id"]
        pr = db.query(ProductRecord).filter(
            ProductRecord.merchant_id.in_(source_ids)).count()
        fav = db.query(UserMerchantFavorite).filter(
            UserMerchantFavorite.merchant_id.in_(source_ids)).count()
        return {
            "affected_price_records": pr,
            "affected_favorites": fav,
            "target_id": target_id,
            "note": "合并将把源商家的价格记录迁移到目标商家，删除源收藏，软停用源商家",
        }

    def apply(self, db, proposal) -> ApplyResult:
        source_ids: List[int] = list(proposal.payload["source_ids"])
        target_id: int = proposal.payload["target_id"]

        # 1. 快照所有受影响行（供 revert）
        snapshot = {
            "product_records": [
                {"id": r.id, "merchant_id": r.merchant_id}
                for r in db.query(ProductRecord)
                    .filter(ProductRecord.merchant_id.in_(source_ids)).all()
            ],
            "favorites": [
                {"id": f.id, "user_id": f.user_id, "merchant_id": f.merchant_id}
                for f in db.query(UserMerchantFavorite)
                    .filter(UserMerchantFavorite.merchant_id.in_(source_ids)).all()
            ],
            "sources": [
                {"id": m.id, "is_open": m.is_open, "name": m.name}
                for m in db.query(Merchant).filter(Merchant.id.in_(source_ids)).all()
            ],
        }

        # 2. 迁移 ProductRecord.merchant_id → target
        db.query(ProductRecord).filter(
            ProductRecord.merchant_id.in_(source_ids)
        ).update({ProductRecord.merchant_id: target_id}, synchronize_session=False)

        # 3. 删除源收藏（目标已收藏的去重由 UNIQUE(user_id, merchant_id) 保证；
        #    若用户同时收藏了源与目标，迁移到 target 会撞 UNIQUE，故直接删源而非迁移）
        db.query(UserMerchantFavorite).filter(
            UserMerchantFavorite.merchant_id.in_(source_ids)
        ).delete(synchronize_session=False)

        # 4. 软停用源商家：is_open=False + 名称加 [已合并] 前缀
        for m in db.query(Merchant).filter(Merchant.id.in_(source_ids)).all():
            m.is_open = False
            if not m.name.startswith(_MERGED_PREFIX):
                m.name = f"{_MERGED_PREFIX}{m.name}"

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"source_ids": source_ids, "target_id": target_id},
            summary=f"已合并 {len(source_ids)} 个商家到 {target_id}",
        )

    def revert(self, db, proposal) -> None:
        snap = proposal.snapshot or {}

        # 1. 还原 ProductRecord.merchant_id
        for item in snap.get("product_records", []):
            pr = db.query(ProductRecord).get(item["id"])
            if pr is not None:
                pr.merchant_id = item["merchant_id"]

        # 2. 重新插入源收藏（合并时被删除，按快照恢复；撞 UNIQUE 的由 db.flush 时
        #    捕获并跳过——理论上源收藏在快照后即被删，恢复时不会再撞目标）
        for item in snap.get("favorites", []):
            existing = db.query(UserMerchantFavorite).filter(
                UserMerchantFavorite.user_id == item["user_id"],
                UserMerchantFavorite.merchant_id == item["merchant_id"],
            ).first()
            if existing is None:
                db.add(UserMerchantFavorite(
                    user_id=item["user_id"], merchant_id=item["merchant_id"],
                ))

        # 3. 复活源商家：还原 is_open + 名称（去前缀）
        for s in snap.get("sources", []):
            m = db.query(Merchant).get(s["id"])
            if m is not None:
                m.is_open = s["is_open"]
                # 名称还原：去合并时加的前缀，并优先信任快照里的原始名（幂等）
                if s.get("name"):
                    m.name = s["name"]
                elif m.name.startswith(_MERGED_PREFIX):
                    m.name = m.name[len(_MERGED_PREFIX):]
