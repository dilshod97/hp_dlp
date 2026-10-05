"""Ma'lumotlar bazasi ulanishi (SQLModel)."""
import logging

from sqlmodel import SQLModel, Session, create_engine, select

from .config import settings

log = logging.getLogger("db")

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _seed_admin()
    _seed_policy()


def _seed_policy() -> None:
    from .models import Policy
    with Session(engine) as session:
        if session.get(Policy, 1) is None:
            session.add(Policy(id=1))
            session.commit()
            log.info("Standart DLP siyosati yaratildi")


def _seed_admin() -> None:
    """Hech qanday foydalanuvchi bo'lmasa, standart admin yaratadi."""
    from .models import User
    from .auth import hash_password

    with Session(engine) as session:
        exists = session.exec(select(User)).first()
        if exists:
            return
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="superadmin",
        )
        session.add(user)
        session.commit()
        log.warning("Standart admin yaratildi: %s (parolni almashtiring!)", settings.admin_username)


def get_session():
    with Session(engine) as session:
        yield session
