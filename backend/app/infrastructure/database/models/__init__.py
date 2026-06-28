# Import all models so they register with Base.metadata.
# Alembic's env.py and test fixtures import this module to ensure all tables
# are known before create_all() / autogenerate is called.
from app.infrastructure.database.models.application import Application
from app.infrastructure.database.models.job_post import JobPost
from app.infrastructure.database.models.resume import Resume
from app.infrastructure.database.models.user import User

__all__ = ["User", "Resume", "JobPost", "Application"]
