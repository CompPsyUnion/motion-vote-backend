import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """测试用户注册"""
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123"
    }

    response = await async_client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient):
    """测试用户登录"""
    # 先注册用户
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123"
    }

    await async_client.post("/api/auth/register", json=user_data)

    # 登录
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }

    response = await async_client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
