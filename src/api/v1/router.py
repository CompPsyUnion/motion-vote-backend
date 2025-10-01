from fastapi import APIRouter

from src.api.v1.endpoints import auth, users, activities, debates, participants, participant_resources, votes, screen, statistics

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 用户管理路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 活动管理路由
api_router.include_router(
    activities.router, prefix="/activities", tags=["activities"])

# 辩题管理路由
api_router.include_router(debates.router, tags=["debates"])

# 参与者管理路由 - activities下的participants资源
api_router.include_router(
    participants.router, prefix="/activities", tags=["participants"])

# 独立的参与者资源路由 (links, qrcodes等)
api_router.include_router(
    participant_resources.router, tags=["participants"])

# 投票系统路由
api_router.include_router(votes.router, prefix="/votes", tags=["votes"])

# 大屏展示路由
api_router.include_router(screen.router, prefix="/screen", tags=["screen"])

# 数据统计路由
api_router.include_router(
    statistics.router, prefix="/statistics", tags=["statistics"])
