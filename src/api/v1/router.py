from fastapi import APIRouter

from src.api.v1.endpoints import auth, users, activities, debates, participants, votes, screen, statistics

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 用户管理路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 活动管理路由
api_router.include_router(
    activities.router, prefix="/activities", tags=["activities"])

# 辩题管理路由
api_router.include_router(debates.router, prefix="/debates", tags=["debates"])

# 参与者管理路由
api_router.include_router(
    participants.router, prefix="/participants", tags=["participants"])

# 投票系统路由
api_router.include_router(votes.router, prefix="/votes", tags=["votes"])

# 大屏展示路由
api_router.include_router(screen.router, prefix="/screen", tags=["screen"])

# 数据统计路由
api_router.include_router(
    statistics.router, prefix="/statistics", tags=["statistics"])
