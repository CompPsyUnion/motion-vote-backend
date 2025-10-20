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
from src.utils.logger import app_logger


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
    # 注意：当 allow_origins 为 ['*'] 时，必须设置 allow_credentials=False
    # 否则会导致所有跨域请求被拒绝（包括 WebSocket）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # 使用通配符时必须为 False
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
        app_logger.info("🚀 Application starting up...")

        # 初始化数据库
        try:
            init_database()
            app_logger.info("✅ Database initialized successfully")
        except Exception as e:
            app_logger.error(f"❌ Database initialization failed: {e}")

        # 初始化Redis连接（测试连接）
        try:
            redis_client = RedisClient.get_instance()
            redis_client.ping()
            app_logger.info("✅ Redis connection successful")
        except Exception as e:
            app_logger.error(f"❌ Redis connection failed: {e}")

        app_logger.info(
            f"✅ Application started successfully on {settings.app_name} v{settings.app_version}")
        app_logger.info(f"📋 CORS Origins: {settings.cors_origins}")
        app_logger.info(
            f"🔐 CORS Credentials: False (required when using wildcard)")
        app_logger.info(f"🔌 WebSocket endpoint: /api/ws/screen/")

        yield

        # 关闭Redis连接
        app_logger.info("🛑 Application shutting down...")
        RedisClient.close()
        app_logger.info("✅ Application shut down complete")

    app.router.lifespan_context = lifespan

    return app


app = create_app()
