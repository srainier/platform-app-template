import os

# Set env vars BEFORE any app import to prevent pydantic-settings
# from failing at module load time during test collection.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
