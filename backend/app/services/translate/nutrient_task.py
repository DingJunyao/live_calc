# backend/app/services/translate/nutrient_task.py
"""未映射营养素 AI 翻译任务。

取 usda_food_nutrients 中 name_zh 为空的 distinct name，用 AI（营养学专用 prompt）
翻译，写回 name_zh。营养素名多为缩写/脂肪酸记号（MUFA、12:1 等），机翻不准，故主用 AI。
"""
import logging
import threading
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.config import settings
from app.models.usda import UsdaFoodNutrient, UsdaTask
from app.services.translate.registry import get_translator, find_provider_section
from app.services.translate.base import NUTRIENT_TRANSLATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


class TranslateNutrientsTask:
    def __init__(self, db: Session):
        self.db = db

    async def run(self, provider: str, config_dict: dict, batch_size: int = 50,
                  cancel_event: "threading.Event | None" = None,
                  force: bool = False) -> dict:
        section = find_provider_section(config_dict, provider)
        if not section:
            raise ValueError(f"配置中未找到 provider: {provider}")
        translator = get_translator(provider, section, timeout=settings.translate_http_timeout)

        task = UsdaTask(task_type="translate_nutrients", status="running", provider=provider)
        self.db.add(task); self.db.commit(); self.db.refresh(task)

        if force:
            # 强制重翻：清空所有 name_zh
            self.db.query(UsdaFoodNutrient).update(
                {UsdaFoodNutrient.name_zh: None}, synchronize_session=False
            )
            self.db.commit()
        # 取未映射的 distinct 营养素名（name_zh 为空）
        names = [r[0] for r in self.db.query(distinct(UsdaFoodNutrient.name))
                 .filter(UsdaFoodNutrient.name_zh.is_(None)).all()]
        total = len(names)
        done = 0
        try:
            for i in range(0, total, batch_size):
                if cancel_event and cancel_event.is_set():
                    logger.info(f"营养素翻译任务被取消（已处理 {done}/{total}）")
                    task.status = "failed"
                    task.error_log = "用户取消了营养素翻译任务"
                    break
                chunk = names[i:i + batch_size]
                translations = None
                for attempt in range(MAX_RETRIES):
                    try:
                        translations = await translator.translate_batch(
                            chunk, system_prompt=NUTRIENT_TRANSLATION_SYSTEM_PROMPT
                        )
                        break
                    except Exception as e:
                        logger.warning(f"营养素翻译批次失败 attempt={attempt}: {e}")
                if translations:
                    # 写回：按原名 update 所有该 name 且未译的行
                    for name, zh in zip(chunk, translations):
                        if zh:
                            self.db.query(UsdaFoodNutrient).filter(
                                UsdaFoodNutrient.name == name,
                                UsdaFoodNutrient.name_zh.is_(None),
                            ).update({UsdaFoodNutrient.name_zh: zh}, synchronize_session=False)
                            done += 1
                self.db.commit()
                task.progress = {"done": done, "total": total}
                self.db.commit()
            task.status = "success"
        except Exception as e:
            task.status = "failed"; task.error_log = str(e)
            logger.exception("营养素翻译任务失败")
        finally:
            self.db.commit()
        return {"translated": done, "total": total}
