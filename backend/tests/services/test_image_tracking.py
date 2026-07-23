"""Test update_image_refs function."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.image_tracking import ImageTracking
from app.services.image_tracking import update_image_refs


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestUpdateImageRefs:
    def test_add_new_key(self, db_session):
        update_image_refs(db_session, set(), {"recipes/a.jpg"})
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row is not None
        assert row.ref_count == 1
        assert row.file_size == 0

    def test_remove_key(self, db_session):
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=1))
        db_session.commit()
        before = datetime.now(timezone.utc)
        update_image_refs(db_session, {"recipes/a.jpg"}, set())
        after = datetime.now(timezone.utc)
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.ref_count == 0
        assert row.last_used_at is not None
        # SQLite strips tzinfo on read-back, so compare in naive UTC
        before_naive = before.replace(tzinfo=None)
        after_naive = after.replace(tzinfo=None)
        stored_naive = row.last_used_at.replace(tzinfo=None)
        assert before_naive <= stored_naive <= after_naive

    def test_increment_existing(self, db_session):
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=1))
        db_session.commit()
        update_image_refs(db_session, set(), {"recipes/a.jpg", "recipes/b.jpg"})
        rows = {r.key: r for r in db_session.query(ImageTracking).all()}
        assert rows["recipes/a.jpg"].ref_count == 2
        assert rows["recipes/b.jpg"].ref_count == 1

    def test_decrement_from_two_to_one(self, db_session):
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=2))
        db_session.commit()
        update_image_refs(db_session, {"recipes/a.jpg"}, set())
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.ref_count == 1  # 2 - 1 = 1，还未到 0
        assert row.last_used_at is None  # 未到 0 不记

    def test_from_zero_to_positive_clears_last_used(self, db_session):
        past = datetime.now(timezone.utc) - timedelta(days=10)
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=0, last_used_at=past))
        db_session.commit()
        update_image_refs(db_session, set(), {"recipes/a.jpg"})
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.ref_count == 1
        assert row.last_used_at is None  # 清了

    def test_dont_overwrite_existing_last_used_at(self, db_session):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None)
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=0, last_used_at=past))
        db_session.commit()
        update_image_refs(db_session, {"recipes/a.jpg"}, set())
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.ref_count == 0
        # SQLite strips tzinfo on read-back, so compare in naive UTC
        assert row.last_used_at.replace(tzinfo=None) == past

    def test_no_change_does_nothing(self, db_session):
        update_image_refs(db_session, {"recipes/a.jpg"}, {"recipes/a.jpg"})
        assert db_session.query(ImageTracking).count() == 0

    def test_file_sizes_new_row(self, db_session):
        update_image_refs(db_session, set(), {"recipes/a.jpg"}, file_sizes={"recipes/a.jpg": 1024})
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.file_size == 1024

    def test_file_sizes_existing_key_not_overwritten(self, db_session):
        db_session.add(ImageTracking(key="recipes/a.jpg", ref_count=1, file_size=512))
        db_session.commit()
        update_image_refs(db_session, set(), {"recipes/a.jpg"}, file_sizes={"recipes/a.jpg": 9999})
        row = db_session.query(ImageTracking).filter_by(key="recipes/a.jpg").first()
        assert row.ref_count == 2
        assert row.file_size == 512
