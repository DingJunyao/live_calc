"""Test ImageTracking model creation and constraints."""

import pytest
import sqlalchemy
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.image_tracking import ImageTracking  # noqa


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestImageTrackingModel:
    def test_create_record(self, db_session):
        record = ImageTracking(
            key="recipes/test.jpg",
            ref_count=2,
            file_size=102400,
        )
        db_session.add(record)
        db_session.commit()

        saved = db_session.query(ImageTracking).filter_by(key="recipes/test.jpg").first()
        assert saved is not None
        assert saved.ref_count == 2
        assert saved.file_size == 102400
        assert saved.last_used_at is None
        assert saved.created_at is not None
        assert saved.updated_at is not None

    def test_duplicate_key_raises(self, db_session):
        r1 = ImageTracking(key="recipes/a.jpg")
        r2 = ImageTracking(key="recipes/a.jpg")
        db_session.add(r1)
        db_session.commit()
        db_session.add(r2)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_last_used_at(self, db_session):
        now = datetime.now(timezone.utc)
        record = ImageTracking(key="recipes/test.jpg", last_used_at=now)
        db_session.add(record)
        db_session.commit()
        saved = db_session.query(ImageTracking).filter_by(key="recipes/test.jpg").first()
        assert saved.last_used_at is not None

    def test_content_hash_nullable(self, db_session):
        record = ImageTracking(key="recipes/test.jpg")
        db_session.add(record)
        db_session.commit()
        saved = db_session.query(ImageTracking).filter_by(key="recipes/test.jpg").first()
        assert saved.content_hash is None
