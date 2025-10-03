"""投票服务模块

处理投票相关的业务逻辑，包括：
- 参与者入场验证
- 投票操作和改票
- 投票状态查询
- 投票结果统计
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.core.websocket import manager
from src.models.activity import Activity
from src.models.debate import Debate
from src.models.vote import Participant, Vote, VoteHistory
from src.schemas.debate import DebateStatus
from src.schemas.vote import (ActivityInfo, ParticipantInfo, VotePosition,
                              VoteResults, VoteStatus)


class VoteService:
    """投票服务类"""

    def __init__(self, db: Session):
        self.db = db

    def _get_activity_settings(self, activity_id: str) -> Dict[str, Any]:
        """获取活动的投票设置"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            return {}

        settings = getattr(activity, 'settings', {})
        if not settings:
            return {}

        # 如果settings是字典直接返回，如果是对象需要转换
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

        # 使用原生SQL更新以避免类型问题
        now = datetime.now(timezone.utc)

        # 检查是否首次入场
        if not getattr(participant, 'checked_in', False):
            # 首次入场，更新所有字段
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
            # 已入场，只更新会话信息
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

        # 返回结果
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
        """参与者对辩题进行投票"""

        # 验证会话令牌
        participant = self.db.query(Participant).filter(
            Participant.session_token == session_token
        ).first()
        if not participant:
            raise HTTPException(
                status_code=401, detail=f"无效的会话令牌: {session_token}")

        # 验证辩题是否存在
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail=f"辩题不存在: {debate_id}")

        # 验证辩题是否属于参与者的活动
        if str(debate.activity_id) != str(participant.activity_id):
            raise HTTPException(
                status_code=403,
                detail=f"无权限为此辩题投票 - 辩题活动ID: {debate.activity_id}, 参与者活动ID: {participant.activity_id}"
            )

        # 检查辩题状态是否允许投票
        allowed_statuses = [DebateStatus.ongoing, DebateStatus.final_vote]
        if debate.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"辩题当前不允许投票 - 当前状态: {debate.status}, 允许状态: {[s.value for s in allowed_statuses]}"
            )

        # 查找现有投票
        existing_vote = self.db.query(Vote).filter(
            Vote.participant_id == participant.id,
            Vote.debate_id == debate_id
        ).first()

        # 获取活动投票配置
        vote_config = self._get_vote_config(str(debate.activity_id))
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        if existing_vote:
            # 改票逻辑
            if not allow_vote_change:
                raise HTTPException(status_code=400, detail="不允许改票")

            current_change_count = getattr(existing_vote, 'change_count', 0)
            if current_change_count >= max_vote_changes:
                raise HTTPException(status_code=400, detail="已达到最大改票次数")

            if getattr(existing_vote, 'is_final', False):
                raise HTTPException(status_code=400, detail="投票已锁定，无法修改")

            # 记录投票历史
            vote_history = VoteHistory(
                vote_id=str(existing_vote.id),
                old_position=getattr(existing_vote, 'position'),
                new_position=position
            )
            self.db.add(vote_history)

            # 使用原生SQL更新投票
            new_change_count = current_change_count + 1
            self.db.execute(
                text("""
                    UPDATE votes 
                    SET position = :position,
                        change_count = :change_count,
                        updated_at = :now
                    WHERE id = :id
                """),
                {
                    "position": position.value,
                    "change_count": new_change_count,
                    "now": datetime.now(timezone.utc),
                    "id": str(existing_vote.id)
                }
            )

            remaining_changes = max_vote_changes - new_change_count
            vote_id = str(existing_vote.id)

        else:
            # 新投票
            new_vote = Vote(
                participant_id=str(participant.id),
                debate_id=debate_id,
                position=position,
                change_count=0,
                is_final=False
            )
            self.db.add(new_vote)
            self.db.flush()  # 获取ID

            remaining_changes = max_vote_changes
            vote_id = str(new_vote.id)

        self.db.commit()

        # 广播投票更新到 WebSocket 连接
        try:
            # 获取最新的投票结果用于广播
            vote_results = self.get_debate_results(debate_id)
            import asyncio
            asyncio.create_task(
                manager.broadcast_vote_update(
                    str(debate.activity_id),
                    debate_id,
                    {
                        "vote_results": vote_results.__dict__,
                        "participant_id": str(participant.id),
                        "position": position.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            )
        except Exception as e:
            # WebSocket 广播失败不应该影响投票操作
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
        """获取参与者的投票状态"""

        # 验证会话令牌
        participant = self.db.query(Participant).filter(
            Participant.session_token == session_token
        ).first()
        if not participant:
            raise HTTPException(status_code=401, detail="无效的会话令牌")

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 查找投票记录
        vote = self.db.query(Vote).filter(
            Vote.participant_id == participant.id,
            Vote.debate_id == debate_id
        ).first()

        # 获取活动投票配置
        vote_config = self._get_vote_config(str(debate.activity_id))
        max_vote_changes = vote_config['max_vote_changes']
        allow_vote_change = vote_config['allow_vote_change']

        if vote:
            current_change_count = getattr(vote, 'change_count', 0)
            remaining_changes = max_vote_changes - current_change_count
            can_change = (
                allow_vote_change and
                remaining_changes > 0 and
                not getattr(vote, 'is_final', False) and
                str(getattr(debate, 'status', '')) in ["active", "draft"]
            )

            return VoteStatus(
                hasVoted=True,
                position=VotePosition(getattr(vote, 'position', 'abstain')),
                votedAt=getattr(vote, 'created_at'),
                remainingChanges=remaining_changes,
                canVote=False,  # 已投票
                canChange=can_change
            )
        else:
            return VoteStatus(
                hasVoted=False,
                position=None,
                votedAt=None,
                remainingChanges=max_vote_changes,
                canVote=str(debate.status) in ["active", "draft"],
                canChange=False  # 未投票，无法改票
            )

    def get_debate_results(self, debate_id: str) -> VoteResults:
        """获取辩题的投票统计结果"""

        # 验证辩题
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="辩题不存在")

        # 统计投票数据
        total_votes = self.db.query(Vote).filter(
            Vote.debate_id == debate_id).count()
        pro_votes = self.db.query(Vote).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.pro
        ).count()
        con_votes = self.db.query(Vote).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.con
        ).count()
        abstain_votes = self.db.query(Vote).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.abstain
        ).count()

        # 计算百分比
        pro_percentage = (pro_votes / total_votes *
                          100) if total_votes > 0 else 0
        con_percentage = (con_votes / total_votes *
                          100) if total_votes > 0 else 0
        abstain_percentage = (abstain_votes / total_votes *
                              100) if total_votes > 0 else 0

        # 确定获胜方
        winner = None
        if pro_votes > con_votes:
            winner = "pro"
        elif con_votes > pro_votes:
            winner = "con"
        else:
            winner = "tie"

        # 检查是否锁定（简化处理）
        debate_status = str(getattr(debate, 'status', ''))
        is_locked = debate_status == "ended"
        locked_at = getattr(debate, 'updated_at') if is_locked else None

        return VoteResults(
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
