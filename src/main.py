import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from src.api.v1.router import api_router
from src.config import settings
from src.core.database import init_database
from src.core.exceptions import AppException
from src.core.redis import RedisClient


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="辩论活动实时投票互动系统 - 后端API接口文档",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 信任主机中间件
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # 请求ID中间件
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response

    # 异常处理
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "code": exc.code,
                "timestamp": time.time()
            }
        )

    # 通用异常处理
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal server error: {exc}",
                "code": "INTERNAL_ERROR",
                "timestamp": time.time()
            }
        )

    # 包含API路由
    app.include_router(api_router, prefix="/api")

    # 添加启动事件
    # 使用 lifespan 事件处理器替代 on_event

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用启动和关闭时执行"""
        # 初始化数据库
        init_database()

        # 初始化Redis连接（测试连接）
        try:
            redis_client = RedisClient.get_instance()
            redis_client.ping()
            print("✅ Redis连接成功")
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")

        yield

        # 关闭Redis连接
        RedisClient.close()

    app.router.lifespan_context = lifespan

    return app


app = create_app()
