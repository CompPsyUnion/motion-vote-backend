"""基于Redis的投票服务模块

使用Redis作为投票数据的主存储，提供高性能的投票操作：
- 实时投票统计
- 高并发支持
- 原子性操作
- 投票历史记录
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.core.redis import get_redis
from src.core.websocket import manager
from src.models.activity import Activity
from src.models.debate import Debate
from src.models.vote import Participant
from src.schemas.debate import DebateStatus
from src.schemas.vote import (ActivityInfo, ParticipantInfo, VotePosition,
                              VoteResults, VoteStatus)


class RedisVoteService:
    """基于Redis的投票服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.redis: redis.Redis = get_redis()

    # Redis Key 模式
    @staticmethod
    def _vote_key(debate_id: str, participant_id: str) -> str:
        """投票记录的key"""
        return f"vote:{debate_id}:{participant_id}"

    @staticmethod
    def _debate_votes_key(debate_id: str) -> str:
        """辩题投票集合的key (Set类型，存储所有投票的participant_id)"""
        return f"debate:{debate_id}:votes"

    @staticmethod
    def _debate_position_key(debate_id: str, position: str) -> str:
        """辩题特定立场投票集合的key"""
        return f"debate:{debate_id}:position:{position}"

    @staticmethod
    def _debate_results_key(debate_id: str) -> str:
        """辩题投票结果缓存的key"""
        return f"debate:{debate_id}:results"

    @staticmethod
    def _vote_history_key(debate_id: str, participant_id: str) -> str:
        """投票历史记录的key (List类型)"""
        return f"vote:{debate_id}:{participant_id}:history"

    @staticmethod
    def _session_key(session_token: str) -> str:
        """会话信息的key"""
        return f"session:{session_token}"

    def _get_activity_settings(self, activity_id: str) -> Dict[str, Any]:
        """获取活动的投票设置"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            return {}

        settings = getattr(activity, 'settings', {})
        if not settings:
            return {}

        if hasattr(settings, '__dict__'):
            settings_dict = settings.__dict__
        else:
            settings_dict = settings if isinstance(settings, dict) else {}

        return settings_dict

    def _get_vote_config(self, activity_id: str) -> Dict[str, Any]:
        """获取投票相关配置"""
        settings = self._get_activity_settings(activity_id)

        return {
            'max_vote_changes': settings.get('max_vote_changes', settings.get('maxVoteChanges', 3)),
            'allow_vote_change': settings.get('allow_vote_change', settings.get('allowVoteChange', True)),
            'auto_lock_votes': settings.get('auto_lock_votes', settings.get('autoLockVotes', False)),
            'lock_vote_delay': settings.get('lock_vote_delay', settings.get('lockVoteDelay', 300)),
            'anonymous_voting': settings.get('anonymous_voting', settings.get('anonymousVoting', True)),
            'require_check_in': settings.get('require_check_in', settings.get('requireCheckIn', True))
        }

    def participant_enter(
        self,
        activity_id: str,
        participant_code: str,
        device_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:
        """参与者入场验证和会话创建"""

        # 验证活动是否存在
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="活动不存在")

        # 验证参与者是否存在
        participant = self.db.query(Participant).filter(
            Participant.activity_id == activity_id,
            Participant.code == participant_code
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="参与者不存在或编号错误")

        # 生成会话令牌
        session_token = str(uuid.uuid4())

        # 更新数据库中的参与者信息
        now = datetime.now(timezone.utc)
        if not getattr(participant, 'checked_in', False):
            from sqlalchemy import text
            self.db.execute(
                text("""
                    UPDATE participants 
                    SET session_token = :token, 
                        device_fingerprint = :fingerprint,
                        checked_in = true,
                        checked_in_at = :now
                    WHERE id = :id
                """),
                {
                    "token": session_token,
                    "fingerprint": device_fingerprint,
                    "now": now,
                    "id": str(participant.id)
                }
            )
        else:
            from sqlalchemy import text
            self.db.execute(
                text("""
                    UPDATE participants 
                    SET session_token = :token, 
                        device_fingerprint = :fingerprint
                    WHERE id = :id
                """),
                {
                    "token": session_token,
                    "fingerprint": device_fingerprint,
                    "id": str(participant.id)
                }
            )

        self.db.commit()

        # 在Redis中存储会话信息（24小时过期）
        session_data = {
            "participant_id": str(participant.id),
            "activity_id": activity_id,
            "participant_code": participant_code,
            "device_fingerprint": device_fingerprint,
            "created_at": now.isoformat()
        }
        session_key = self._session_key(session_token)
        self.redis.setex(
            session_key,
            86400,  # 24小时
            json.dumps(session_data)
        )

        return {
            "session_token": session_token,
            "activity": ActivityInfo(
                id=str(activity.id),
                name=getattr(activity, 'name', ''),
                status=str(getattr(activity, 'status', ''))
            ),
            "participant": ParticipantInfo(
                id=str(participant.id),
                code=getattr(participant, 'code', ''),
                name=getattr(participant, 'name', '')
            )
        }

    def _get_participant_from_session(self, session_token: str) -> tuple[str, str]:
        """从会话令牌获取参与者ID和活动ID"""
        session_key = self._session_key(session_token)
        session_data_str = self.redis.get(session_key)

        if not session_data_str:
            raise HTTPException(status_code=401, detail="无效或已过期的会话令牌")

        # 确保类型正确
        session_data_str = str(session_data_str) if session_data_str else ""
        session_data = json.loads(session_data_str)
        return session_data['participant_id'], session_data['activity_id']

    def vote_for_debate(
        self,
        debate_id: str,
        session_token: str,
        position: VotePosition
    ) -> Dict[str, Any]:
        """参与者对辩题进行投票（使用Redis）"""

        # 从会话获取参与者信息
        participant_id, activity_id = self._get_participant_from_session(session_token)

        # 验证辩题是否存在
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail=f"辩题不存在: {debate_id}")

        # 验证辩题是否属于参与者的活动
        if str(debate.activity_id) != activity_id:
            raise HTTPException(
                status_code=403,
                detail="无权限为此辩题投票"
            )

        # 检查辩题状态是否允许投票
        allowed_statuses = [DebateStatus.ongoing, DebateStatus.final_vote]
        if debate.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"辩题当前不允许投票 - 当前状态: {debate.status}"
            )

        # 获取投票配置
        vote_config = self._get_vote_config(activity_id)
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        # 使用Redis Pipeline确保原子性
        pipe = self.redis.pipeline()

        vote_key = self._vote_key(debate_id, participant_id)
        existing_vote_str = self.redis.get(vote_key)

        if existing_vote_str:
            # 改票逻辑
            existing_vote_str = str(existing_vote_str) if existing_vote_str else ""
            existing_vote = json.loads(existing_vote_str)

            if not allow_vote_change:
                raise HTTPException(status_code=400, detail="不允许改票")

            current_change_count = existing_vote.get('change_count', 0)
            if current_change_count >= max_vote_changes:
                raise HTTPException(status_code=400, detail="已达到最大改票次数")

            if existing_vote.get('is_final', False):
                raise HTTPException(status_code=400, detail="投票已锁定，无法修改")

            old_position = existing_vote['position']

            # 记录投票历史
            history_record = {
                "old_position": old_position,
                "new_position": position.value,
                "changed_at": datetime.now(timezone.utc).isoformat()
            }
            history_key = self._vote_history_key(debate_id, participant_id)
            pipe.lpush(history_key, json.dumps(history_record))

            # 更新投票记录
            new_vote_data = {
                "participant_id": participant_id,
                "debate_id": debate_id,
                "position": position.value,
                "change_count": current_change_count + 1,
                "is_final": False,
                "created_at": existing_vote['created_at'],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            pipe.set(vote_key, json.dumps(new_vote_data))

            # 更新立场集合
            old_position_key = self._debate_position_key(debate_id, old_position)
            new_position_key = self._debate_position_key(debate_id, position.value)
            pipe.srem(old_position_key, participant_id)
            pipe.sadd(new_position_key, participant_id)

            pipe.execute()

            remaining_changes = max_vote_changes - (current_change_count + 1)
            vote_id = existing_vote.get('vote_id', str(uuid.uuid4()))

        else:
            # 新投票
            vote_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            vote_data = {
                "vote_id": vote_id,
                "participant_id": participant_id,
                "debate_id": debate_id,
                "position": position.value,
                "change_count": 0,
                "is_final": False,
                "created_at": now,
                "updated_at": now
            }

            # 存储投票记录
            pipe.set(vote_key, json.dumps(vote_data))

            # 添加到辩题投票集合
            debate_votes_key = self._debate_votes_key(debate_id)
            pipe.sadd(debate_votes_key, participant_id)

            # 添加到立场集合
            position_key = self._debate_position_key(debate_id, position.value)
            pipe.sadd(position_key, participant_id)

            pipe.execute()

            remaining_changes = max_vote_changes

        # 删除结果缓存，强制重新计算
        results_key = self._debate_results_key(debate_id)
        self.redis.delete(results_key)

        # 广播投票更新到 WebSocket
        try:
            vote_results = self.get_debate_results(debate_id)
            import asyncio
            asyncio.create_task(
                manager.broadcast_vote_update(
                    activity_id,
                    debate_id,
                    {
                        "vote_results": vote_results.dict(),
                        "participant_id": participant_id,
                        "position": position.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            )
        except Exception as e:
            print(f"WebSocket 广播失败: {e}")

        return {
            "vote_id": vote_id,
            "remaining_changes": remaining_changes
        }

    def get_vote_status(
        self,
        debate_id: str,
        session_token: str
    ) -> VoteStatus:
        """获取参与者的投票状态（从Redis读取）"""

        # 从会话获取参与者信息
        participant_id, activity_id = self._get_participant_from_session(session_token)

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 获取投票配置
        vote_config = self._get_vote_config(activity_id)
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        # 从Redis获取投票记录
        vote_key = self._vote_key(debate_id, participant_id)
        vote_str = self.redis.get(vote_key)

        if vote_str:
            vote_str = str(vote_str) if vote_str else ""
            vote_data = json.loads(vote_str)
            current_change_count = vote_data.get('change_count', 0)
            remaining_changes = max_vote_changes - current_change_count
            can_change = (
                allow_vote_change and
                remaining_changes > 0 and
                not vote_data.get('is_final', False) and
                str(debate.status) in ["ongoing", "final_vote"]
            )

            return VoteStatus(
                hasVoted=True,
                position=VotePosition(vote_data['position']),
                votedAt=datetime.fromisoformat(vote_data['created_at']),
                remainingChanges=remaining_changes,
                canVote=False,
                canChange=can_change
            )
        else:
            return VoteStatus(
                hasVoted=False,
                position=None,
                votedAt=None,
                remainingChanges=max_vote_changes,
                canVote=str(debate.status) in ["ongoing", "final_vote"],
                canChange=False
            )

    def get_debate_results(self, debate_id: str) -> VoteResults:
        """获取辩题的投票统计结果（从Redis计算）"""

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 尝试从缓存获取结果
        results_key = self._debate_results_key(debate_id)
        cached_results = self.redis.get(results_key)

        if cached_results:
            cached_results = str(cached_results) if cached_results else ""
            results_data = json.loads(cached_results)
            return VoteResults(**results_data)

        # 从Redis计算实时结果
        pro_key = self._debate_position_key(debate_id, VotePosition.pro.value)
        con_key = self._debate_position_key(debate_id, VotePosition.con.value)
        abstain_key = self._debate_position_key(debate_id, VotePosition.abstain.value)

        # type: ignore 用于解决Redis类型推断问题
        pro_votes = int(self.redis.scard(pro_key) or 0)  # type: ignore
        con_votes = int(self.redis.scard(con_key) or 0)  # type: ignore
        abstain_votes = int(self.redis.scard(abstain_key) or 0)  # type: ignore
        total_votes = pro_votes + con_votes + abstain_votes

        # 计算百分比
        pro_percentage = (pro_votes / total_votes * 100) if total_votes > 0 else 0
        con_percentage = (con_votes / total_votes * 100) if total_votes > 0 else 0
        abstain_percentage = (abstain_votes / total_votes * 100) if total_votes > 0 else 0

        # 确定获胜方
        winner = None
        if pro_votes > con_votes:
            winner = "pro"
        elif con_votes > pro_votes:
            winner = "con"
        else:
            winner = "tie"

        # 检查是否锁定
        debate_status = str(debate.status)
        is_locked = debate_status == "ended"
        locked_at = getattr(debate, 'updated_at') if is_locked else None

        results = VoteResults(
            debateId=debate_id,
            totalVotes=total_votes,
            proVotes=pro_votes,
            conVotes=con_votes,
            abstainVotes=abstain_votes,
            proPercentage=round(pro_percentage, 2),
            conPercentage=round(con_percentage, 2),
            abstainPercentage=round(abstain_percentage, 2),
            winner=winner,
            is_locked=is_locked,
            locked_at=locked_at
        )

        # 缓存结果（10秒）
        self.redis.setex(results_key, 10, json.dumps(results.dict()))

        return results

    def clear_debate_votes(self, debate_id: str) -> Dict[str, Any]:
        """清空辩题的所有投票数据"""

        # 获取所有投票的参与者
        debate_votes_key = self._debate_votes_key(debate_id)
        participant_ids_result = self.redis.smembers(debate_votes_key)  # type: ignore
        participant_ids: set = set(participant_ids_result) if participant_ids_result else set()  # type: ignore

        pipe = self.redis.pipeline()

        # 删除每个投票记录
        for participant_id in participant_ids:
            vote_key = self._vote_key(debate_id, participant_id)
            history_key = self._vote_history_key(debate_id, participant_id)
            pipe.delete(vote_key)
            pipe.delete(history_key)

        # 删除立场集合
        for position in [VotePosition.pro.value, VotePosition.con.value, VotePosition.abstain.value]:
            position_key = self._debate_position_key(debate_id, position)
            pipe.delete(position_key)

        # 删除投票集合和结果缓存
        pipe.delete(debate_votes_key)
        pipe.delete(self._debate_results_key(debate_id))

        pipe.execute()

        return {
            "success": True,
            "message": f"已清空辩题 {debate_id} 的所有投票数据",
            "cleared_votes": len(participant_ids)
        }
