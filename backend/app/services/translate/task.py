# backend/app/services/translate/task.py
"""翻译任务：增量（只译 pending）+ 进度写 UsdaTask + 单批重试 3 次。"""
import logging
import threading
from sqlalchemy.orm import Session
from app.config import settings
from app.models.usda import UsdaFood, UsdaTask
from app.services.translate.registry import get_translator, find_provider_section

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


class TranslateTask:
    def __init__(self, db: Session):
        self.db = db

    async def run(self, provider: str, config_dict: dict, batch_size: int = 50,
                  cancel_event: "threading.Event | None" = None,
                  force: bool = False) -> dict:
        section = find_provider_section(config_dict, provider)
        if not section:
            raise ValueError(f"配置中未找到 provider: {provider}")
        translator = get_translator(provider, section, timeout=settings.translate_http_timeout)

        task = UsdaTask(task_type="translate", status="running", provider=provider)
        self.db.add(task); self.db.commit(); self.db.refresh(task)

        if force:
            # 强制重翻：把所有 translate_status 重置为 pending
            self.db.query(UsdaFood).filter(
                UsdaFood.translate_status.in_(["done", "error"]),
            ).update({UsdaFood.translate_status: "pending"}, synchronize_session=False)
            self.db.commit()
        foods = self.db.query(UsdaFood).filter(UsdaFood.translate_status == "pending").all()
        total = len(foods)
        done = 0
        try:
            for i in range(0, total, batch_size):
                if cancel_event and cancel_event.is_set():
                    logger.info(f"翻译任务被取消（已处理 {done}/{total}）")
                    task.status = "failed"
                    task.error_log = "用户取消了翻译任务"
                    break
                chunk = foods[i:i + batch_size]
                texts = [f.description for f in chunk]
                translations = None
                for attempt in range(MAX_RETRIES):
                    try:
                        translations = await translator.translate_batch(texts)
                        break
                    except Exception as e:
                        logger.warning(f"翻译批次失败 attempt={attempt}: {e}")
                if translations is None:
                    for f in chunk:
                        f.translate_status = "error"
                else:
                    for f, zh in zip(chunk, translations):
                        f.description_zh = zh or f.description_zh
                        f.translate_status = "done" if zh else "error"
                        done += 1
                self.db.commit()
                task.progress = {"done": done, "total": total}
                self.db.commit()
            task.status = "success"
        except Exception as e:
            task.status = "failed"; task.error_log = str(e)
            logger.error(f"翻译任务失败: {e}")
        finally:
            self.db.commit()
        return {"translated": done, "total": total}
