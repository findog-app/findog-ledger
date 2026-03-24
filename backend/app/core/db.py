from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import verify_password
from app.models import User
from app.schemas import UserCreate, UserUpdate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            is_active=True,
        )
        try:
            user = crud.create_user(session=session, user_create=user_in)
        except IntegrityError:
            session.rollback()
            user = session.exec(
                select(User).where(User.email == settings.FIRST_SUPERUSER)
            ).first()

    if not user:
        return

    verified, _ = verify_password(
        settings.FIRST_SUPERUSER_PASSWORD, user.hashed_password
    )
    if user.is_superuser and user.is_active and verified:
        return

    crud.update_user(
        session=session,
        db_user=user,
        user_in=UserUpdate(
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            is_active=True,
            full_name=user.full_name,
        ),
    )
