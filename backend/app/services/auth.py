from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import User
from app.repositories import users as user_repository

DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = user_repository.get_user_by_email(session=session, email=email)
    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None

    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None

    if updated_password_hash:
        db_user = user_repository.update_user(
            session=session,
            db_user=db_user,
            updates={"hashed_password": updated_password_hash},
        )
    return db_user
