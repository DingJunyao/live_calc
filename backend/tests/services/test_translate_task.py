# backend/tests/services/test_translate_task.py
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.usda import UsdaFood
from app.services.translate.task import TranslateTask


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add_all([
        UsdaFood(fdc_id=1, data_type="foundation", description="Apple, raw", translate_status="pending"),
        UsdaFood(fdc_id=2, data_type="foundation", description="Beef, raw", translate_status="done"),
        UsdaFood(fdc_id=3, data_type="foundation", description="Chicken, raw", translate_status="pending"),
    ])
    s.commit()
    yield s
    s.close()


class FakeTranslator:
    name = "openai"
    async def translate_batch(self, texts):
        return [f"译-{t}" for t in texts]
    async def health_check(self):
        return True


@pytest.mark.asyncio
async def test_only_pending_translated(db):
    config_dict = {"ai": {"providers": {"openai": {"enabled": True, "base_url": "x", "api_key": "y", "model": "z"}}}}
    with patch("app.services.translate.task.get_translator", return_value=FakeTranslator()):
        result = await TranslateTask(db).run(provider="openai", config_dict=config_dict, batch_size=10)
    assert result["translated"] == 2
    assert db.query(UsdaFood).filter(UsdaFood.fdc_id == 1).one().description_zh == "译-Apple, raw"
    assert db.query(UsdaFood).filter(UsdaFood.fdc_id == 1).one().translate_status == "done"
    # fdc=2 原本 done，未被重新翻译（增量）
    assert db.query(UsdaFood).filter(UsdaFood.fdc_id == 2).one().description_zh is None
