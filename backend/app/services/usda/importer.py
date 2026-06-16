# backend/app/services/usda/importer.py
"""USDA 食材入库（upsert），下载与上传共用本管线。"""
from sqlalchemy.orm import Session
from app.models.usda import UsdaFood, UsdaFoodNutrient


class UsdaImporter:
    """按 fdc_id upsert 食材及其营养素。"""

    def __init__(self, db: Session):
        self.db = db

    def import_entries(self, entries: list[dict], batch_size: int = 100) -> dict:
        inserted = updated = 0
        for i, e in enumerate(entries, 1):
            food = self.db.query(UsdaFood).filter(UsdaFood.fdc_id == e["fdc_id"]).first()
            if food is None:
                food = UsdaFood(
                    fdc_id=e["fdc_id"], data_type=e["data_type"],
                    description=e["description"], publication_date=e.get("publication_date"),
                    translate_status="pending",
                )
                self.db.add(food)
                inserted += 1
            else:
                food.data_type = e["data_type"]
                food.description = e["description"]
                food.publication_date = e.get("publication_date")
                food.translate_status = "pending"  # 描述变更，重置翻译
                updated += 1
            self.db.flush()
            self._replace_nutrients(food.fdc_id, e.get("nutrients", []))
            # 分批提交：缩短 SQLite 单次写锁持有，避免长事务阻塞其他请求
            if i % batch_size == 0:
                self.db.commit()
        self.db.commit()
        return {"inserted": inserted, "updated": updated}

    def _replace_nutrients(self, fdc_id: int, nutrients: list[dict]):
        self.db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.fdc_id == fdc_id).delete()
        for n in nutrients:
            self.db.add(UsdaFoodNutrient(
                fdc_id=fdc_id, nutrient_no=n.get("nutrient_no"),
                name=n["name"], name_zh=n.get("name_zh"),
                amount=n["amount"], unit_name=n["unit_name"],
            ))
