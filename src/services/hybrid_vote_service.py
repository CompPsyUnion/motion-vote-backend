"""混合投票服务模块

结合Redis和数据库的优势：
- Redis：实时投票，毫秒级响应
- 数据库：持久化存储，数据安全
- 定时同步：每2秒将Redis数据批量写入数据库
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.core.redis import get_redis
from src.core.websocket import manager
from src.models.activity import Activity
from src.models.debate import Debate
from src.models.vote import Participant, Vote, VoteHistory
from src.schemas.debate import DebateStatus
from src.schemas.vote import (ActivityInfo, ParticipantInfo, VotePosition,
                              VoteResults, VoteStatus)


class HybridVoteService:
    """混合投票服务类 - Redis + 数据库"""

    # 类级别的同步任务
    _sync_task: Optional[asyncio.Task] = None
    _sync_lock = asyncio.Lock()

    def __init__(self, db: Session):
        self.db = db
        self.redis = get_redis()

        # 启动后台同步任务
        if HybridVoteService._sync_task is None:
            HybridVoteService._sync_task = asyncio.create_task(
                self._background_sync_worker()
            )

    # ============ Redis Key 生成 ============

    def _vote_key(self, debate_id: str, participant_id: str) -> str:
        """投票记录的Redis key"""
        return f"vote:{debate_id}:{participant_id}"

    def _debate_votes_key(self, debate_id: str) -> str:
        """辩题所有投票者的Set key"""
        return f"debate:{debate_id}:votes"

    def _debate_position_key(self, debate_id: str, position: str) -> str:
        """辩题某个立场的投票者Set key"""
        return f"debate:{debate_id}:position:{position}"

    def _session_key(self, token: str) -> str:
        """会话信息的Redis key"""
        return f"session:{token}"

    def _dirty_debates_key(self) -> str:
        """需要同步到数据库的辩题ID集合"""
        return "sync:dirty_debates"

    def _debate_cache_key(self, debate_id: str) -> str:
        """辩题信息缓存的Redis key"""
        return f"debate:{debate_id}:info"

    def invalidate_debate_cache(self, debate_id: str):
        """清除辩题缓存（当debate状态更新时调用）"""
        self.redis.delete(self._debate_cache_key(debate_id))  # type: ignore

    def invalidate_activity_config_cache(self, activity_id: str):
        """清除活动配置缓存（当activity settings更新时调用）"""
        cache_key = f"activity:{activity_id}:vote_config"
        self.redis.delete(cache_key)  # type: ignore

    # ============ 核心业务方法 ============

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
        """获取投票相关配置（优先从Redis缓存）"""
        # 尝试从Redis缓存获取
        cache_key = f"activity:{activity_id}:vote_config"
        cached_config = self.redis.get(cache_key)  # type: ignore

        if cached_config:
            return json.loads(str(cached_config))

        # 缓存未命中，从数据库获取
        settings = self._get_activity_settings(activity_id)

        config = {
            'max_vote_changes': settings.get('max_vote_changes', settings.get('maxVoteChanges', 3)),
            'allow_vote_change': settings.get('allow_vote_change', settings.get('allowVoteChange', True)),
            'auto_lock_votes': settings.get('auto_lock_votes', settings.get('autoLockVotes', False)),
            'lock_vote_delay': settings.get('lock_vote_delay', settings.get('lockVoteDelay', 300)),
            'anonymous_voting': settings.get('anonymous_voting', settings.get('anonymousVoting', True)),
            'require_check_in': settings.get('require_check_in', settings.get('requireCheckIn', True))
        }

        # 缓存配置(60秒过期)
        self.redis.setex(cache_key, 60, json.dumps(config))  # type: ignore

        return config

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
        import uuid
        session_token = str(uuid.uuid4())

        # 1. 写入Redis（会话信息，24小时过期）
        session_data = {
            "participant_id": str(participant.id),
            "activity_id": activity_id,
            "participant_code": participant_code,
            "device_fingerprint": device_fingerprint,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.redis.setex(
            self._session_key(session_token),
            86400,  # 24小时
            json.dumps(session_data)
        )

        # 2. 更新数据库（session_token和签到状态）
        now = datetime.now(timezone.utc)
        if not getattr(participant, 'checked_in', False):
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
        self.db.refresh(participant)

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

    def vote_for_debate(
        self,
        debate_id: str,
        session_token: str,
        position: VotePosition
    ) -> Dict[str, Any]:
        """参与者对辩题进行投票（Redis + 定时同步）"""

        # 1. 从Redis验证会话
        session_key = self._session_key(session_token)
        session_data_str = self.redis.get(session_key)  # type: ignore
        if not session_data_str:
            raise HTTPException(status_code=401, detail="会话已过期或无效")

        session_data = json.loads(str(session_data_str))
        participant_id = session_data["participant_id"]
        activity_id = session_data["activity_id"]

        # 2. 验证辩题（优先从Redis缓存读取，避免频繁数据库查询）
        debate_cache_key = f"debate:{debate_id}:info"
        debate_cache = self.redis.get(debate_cache_key)  # type: ignore

        if debate_cache:
            # 从缓存读取
            debate_info = json.loads(str(debate_cache))
            debate_activity_id = debate_info['activity_id']
            debate_status = debate_info['status']
        else:
            # 缓存未命中，从数据库查询并缓存
            debate = self.db.query(Debate).filter(
                Debate.id == debate_id).first()
            if not debate:
                raise HTTPException(status_code=404, detail="辩题不存在")

            debate_activity_id = str(debate.activity_id)
            debate_status = debate.status

            # 缓存辩题信息(30秒过期)
            debate_info = {
                'activity_id': debate_activity_id,
                'status': debate_status
            }
            self.redis.setex(debate_cache_key, 30, json.dumps(
                debate_info))  # type: ignore

        if debate_activity_id != activity_id:
            raise HTTPException(status_code=403, detail="无权限为此辩题投票")

        allowed_statuses = [DebateStatus.ongoing, DebateStatus.final_vote]
        if debate_status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="辩题当前不允许投票")

        # 3. 获取投票配置
        vote_config = self._get_vote_config(activity_id)
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        # 4. 从Redis获取现有投票
        vote_key = self._vote_key(debate_id, participant_id)
        existing_vote_str = self.redis.get(vote_key)  # type: ignore

        pipe = self.redis.pipeline()

        if existing_vote_str:
            # 改票逻辑
            existing_vote = json.loads(str(existing_vote_str))

            if not allow_vote_change:
                raise HTTPException(status_code=400, detail="不允许改票")

            current_change_count = existing_vote.get('change_count', 0)
            if current_change_count >= max_vote_changes:
                raise HTTPException(status_code=400, detail="已达到最大改票次数")

            if existing_vote.get('is_final', False):
                raise HTTPException(status_code=400, detail="投票已锁定，无法修改")

            old_position = existing_vote['position']
            new_change_count = current_change_count + 1

            # 更新投票记录
            vote_data = {
                "vote_id": existing_vote['vote_id'],
                "participant_id": participant_id,
                "debate_id": debate_id,
                "position": position.value,
                "change_count": new_change_count,
                "is_final": False,
                "created_at": existing_vote['created_at'],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Redis原子操作
            pipe.set(vote_key, json.dumps(vote_data))
            pipe.srem(self._debate_position_key(
                debate_id, old_position), participant_id)
            pipe.sadd(self._debate_position_key(
                debate_id, position.value), participant_id)

            # 记录历史到Redis
            history_key = f"{vote_key}:history"
            history_entry = {
                "old_position": old_position,
                "new_position": position.value,
                "changed_at": datetime.now(timezone.utc).isoformat()
            }
            pipe.lpush(history_key, json.dumps(history_entry))

            remaining_changes = max_vote_changes - new_change_count
            vote_id = existing_vote['vote_id']

        else:
            # 新投票
            import uuid
            vote_id = str(uuid.uuid4())

            vote_data = {
                "vote_id": vote_id,
                "participant_id": participant_id,
                "debate_id": debate_id,
                "position": position.value,
                "change_count": 0,
                "is_final": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Redis原子操作
            pipe.set(vote_key, json.dumps(vote_data))
            pipe.sadd(self._debate_votes_key(debate_id), participant_id)
            pipe.sadd(self._debate_position_key(
                debate_id, position.value), participant_id)

            remaining_changes = max_vote_changes

        # 5. 标记辩题为脏数据（需要同步）
        pipe.sadd(self._dirty_debates_key(), debate_id)

        # 删除缓存的结果
        results_cache_key = f"debate:{debate_id}:results"
        pipe.delete(results_cache_key)

        # 执行所有Redis操作
        pipe.execute()

        # 6. 广播WebSocket更新
        try:
            vote_results = self.get_debate_results(debate_id)
            asyncio.create_task(
                manager.broadcast_vote_update(
                    activity_id,
                    debate_id,
                    {
                        "vote_results": vote_results.__dict__,
                        "participant_id": participant_id,
                        "position": position.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            )
        except Exception as e:
            print(f"WebSocket广播失败: {e}")

        return {
            "vote_id": vote_id,
            "remaining_changes": remaining_changes
        }

    def get_vote_status(
        self,
        debate_id: str,
        session_token: str
    ) -> VoteStatus:
        """获取参与者的投票状态（从Redis）"""

        # 从Redis验证会话
        session_key = self._session_key(session_token)
        session_data_str = self.redis.get(session_key)  # type: ignore
        if not session_data_str:
            raise HTTPException(status_code=401, detail="会话已过期或无效")

        session_data = json.loads(str(session_data_str))
        participant_id = session_data["participant_id"]
        activity_id = session_data["activity_id"]

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 从Redis获取投票记录
        vote_key = self._vote_key(debate_id, participant_id)
        vote_data_str = self.redis.get(vote_key)  # type: ignore

        # 获取投票配置
        vote_config = self._get_vote_config(activity_id)
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        if vote_data_str:
            vote_data = json.loads(str(vote_data_str))
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
        """获取辩题的投票统计结果（从Redis，带缓存）"""

        # 尝试从缓存获取
        cache_key = f"debate:{debate_id}:results"
        cached_results = self.redis.get(cache_key)  # type: ignore
        if cached_results:
            cached_data = json.loads(str(cached_results))
            return VoteResults(**cached_data)

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 从Redis统计 (cast to int to satisfy type checker for clients that annotate SCARD as awaitable)
        total_votes = int(cast(int, self.redis.scard(self._debate_votes_key(debate_id))))  # type: ignore
        pro_votes = int(cast(int, self.redis.scard(self._debate_position_key(debate_id, "pro"))))  # type: ignore
        con_votes = int(cast(int, self.redis.scard(self._debate_position_key(debate_id, "con"))))  # type: ignore
        abstain_votes = int(cast(int, self.redis.scard(self._debate_position_key(debate_id, "abstain"))))  # type: ignore

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
        locked_at = getattr(debate, 'updated_at', None) if is_locked else None

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
        self.redis.setex(cache_key, 10, json.dumps(
            results.__dict__, default=str))

        return results

    def clear_debate_votes(self, debate_id: str) -> Dict[str, Any]:
        """清空辩题的所有投票"""

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 获取所有投票者ID
        participant_ids = self.redis.smembers(
            self._debate_votes_key(debate_id))

        # 删除Redis数据
        pipe = self.redis.pipeline()
        for pid in participant_ids:  # type: ignore
            vote_key = self._vote_key(debate_id, str(pid))
            history_key = f"{vote_key}:history"
            pipe.delete(vote_key)
            pipe.delete(history_key)

        pipe.delete(self._debate_votes_key(debate_id))
        pipe.delete(self._debate_position_key(debate_id, "pro"))
        pipe.delete(self._debate_position_key(debate_id, "con"))
        pipe.delete(self._debate_position_key(debate_id, "abstain"))
        pipe.delete(f"debate:{debate_id}:results")
        pipe.execute()

        # 删除数据库记录
        self.db.query(Vote).filter(Vote.debate_id == debate_id).delete()
        self.db.query(VoteHistory).filter(
            VoteHistory.vote_id.in_(
                self.db.query(Vote.id).filter(Vote.debate_id == debate_id)
            )
        ).delete(synchronize_session=False)
        self.db.commit()

        return {
            "message": "投票已清空",
            "deleted_count": len(participant_ids)  # type: ignore
        }

    # ============ 后台同步任务 ============

    async def _background_sync_worker(self):
        """后台工作线程：每2秒同步Redis到数据库"""
        while True:
            try:
                await asyncio.sleep(2)  # 每2秒执行一次
                await self._sync_redis_to_database()
            except Exception as e:
                print(f"[ERROR] 后台同步错误: {e}")
                import traceback
                traceback.print_exc()

    async def _sync_redis_to_database(self):
        """将Redis中的脏数据同步到数据库"""
        async with HybridVoteService._sync_lock:
            # 创建独立的数据库会话
            db = SessionLocal()
            try:
                # 获取所有需要同步的辩题ID
                dirty_debates = self.redis.smembers(self._dirty_debates_key())
                if not dirty_debates:
                    return

                for debate_id in dirty_debates:  # type: ignore
                    await self._sync_debate_votes(str(debate_id), db)

                # 清空脏标记
                self.redis.delete(self._dirty_debates_key())

            except Exception as e:
                print(f"[ERROR] 数据库同步失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()

    async def _sync_debate_votes(self, debate_id: str, db: Session):
        """同步单个辩题的投票数据（批量优化）"""
        try:
            # 获取Redis中的所有投票者
            participant_ids = self.redis.smembers(
                self._debate_votes_key(debate_id))
            if not participant_ids:
                return

            # 批量获取Redis中的投票数据
            vote_data_list = []
            for pid in participant_ids:  # type: ignore
                vote_key = self._vote_key(debate_id, str(pid))
                vote_data_str = self.redis.get(vote_key)  # type: ignore
                if vote_data_str:
                    vote_data = json.loads(str(vote_data_str))
                    vote_data_list.append(vote_data)

            if not vote_data_list:
                return

            # 批量查询数据库中的现有投票（一次查询）
            participant_ids_list = [v['participant_id']
                                    for v in vote_data_list]
            existing_votes = db.query(Vote).filter(
                Vote.debate_id == debate_id,
                Vote.participant_id.in_(participant_ids_list)
            ).all()

            # 创建映射表：participant_id -> existing_vote
            existing_votes_map = {
                str(v.participant_id): v for v in existing_votes}

            # 批量处理更新和插入
            updates = []
            inserts = []

            for vote_data in vote_data_list:
                participant_id = vote_data['participant_id']
                existing_vote = existing_votes_map.get(participant_id)

                if existing_vote:
                    # 检查是否需要更新
                    redis_updated_at = datetime.fromisoformat(
                        vote_data['updated_at'])
                    db_updated_at = getattr(existing_vote, 'updated_at', None)

                    if db_updated_at is None or redis_updated_at > db_updated_at:
                        updates.append({
                            "id": str(existing_vote.id),
                            "position": vote_data['position'],
                            "change_count": vote_data['change_count'],
                            "is_final": vote_data['is_final'],
                            "updated_at": redis_updated_at
                        })
                else:
                    # 创建新投票
                    new_vote = Vote(
                        id=UUID(vote_data['vote_id']),
                        participant_id=UUID(vote_data['participant_id']),
                        debate_id=UUID(debate_id),
                        position=VotePosition(vote_data['position']),
                        change_count=vote_data['change_count'],
                        is_final=vote_data['is_final'],
                        created_at=datetime.fromisoformat(
                            vote_data['created_at']),
                        updated_at=datetime.fromisoformat(
                            vote_data['updated_at'])
                    )
                    inserts.append(new_vote)

            # 批量执行更新
            if updates:
                db.execute(
                    text("""
                        UPDATE votes 
                        SET position = :position,
                            change_count = :change_count,
                            is_final = :is_final,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    updates
                )

            # 批量插入
            if inserts:
                db.add_all(inserts)

            db.commit()

        except Exception as e:
            print(f"[ERROR] 同步辩题 {debate_id} 失败: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
