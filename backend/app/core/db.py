from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.domain import LegacyImportJobStatus
from app.models import LegacyImportJob
from app.services.users import ensure_initial_superuser

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db(session: Session) -> None:
    session.execute(
        update(LegacyImportJob)
        .where(LegacyImportJob.is_active.is_(True))
        .values(
            status=LegacyImportJobStatus.FAILED,
            is_active=False,
            error="Import interrupted by an application restart",
        )
    )
    session.commit()
    ensure_initial_superuser(session)
