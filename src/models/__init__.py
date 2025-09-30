# 导入所有模型以确保它们被注册到SQLAlchemy中
from src.models.activity import Activity, Collaborator
from src.models.debate import Debate
from src.models.user import User
from src.models.vote import Participant, Vote, VoteHistory

__all__ = [
    "User",
    "Activity",
    "Collaborator",
    "Debate",
    "Participant",
    "Vote",
    "VoteHistory"
]
