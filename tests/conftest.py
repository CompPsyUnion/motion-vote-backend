import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.core.database import get_db, Base
from src.config import settings

# 测试数据库配置
SQLALCHEMY_DATABASE_URL = settings.test_database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def db_session():
    # 创建测试表
    Base.metadata.create_all(bind=engine)

    # 创建数据库会话
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # 清理测试表
        Base.metadata.drop_all(bind=engine)
