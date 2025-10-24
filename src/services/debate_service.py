"""辩题服务模块

处理辩题相关的业务逻辑，包括：
- 辩题的CRUD操作
- 辩题状态管理
- 辩题排序
- 投票统计
"""

from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session
from src.models.debate import Debate
from src.models.vote import Vote, VoteHistory
from src.schemas.debate import (DebateCreate, DebateDetailResponse,
                                DebateReorder, DebateResponse, DebateStatus,
                                DebateStatusUpdate, DebateUpdate)
from src.schemas.vote import VoteStats
from src.schemas.vote import VotePosition


class DebateService:
    """辩题服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_debates_paginated(
        self,
        activity_id: str,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "order",
        sort_order: str = "asc"
    ) -> dict:
        """获取辩题列表（分页）

        Args:
            activity_id: 活动ID
            page: 页码
            limit: 每页数量
            search: 搜索关键词
            status: 状态筛选
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            包含辩题列表和分页信息的字典
        """
        # 处理查询参数
        page = max(1, page)
        limit = max(1, min(100, limit))

        # 构建查询
        query = self.db.query(Debate).filter(Debate.activity_id == activity_id)

        # 搜索筛选
        if search and search.strip():
            search_terms = search.strip().split()
            search_conditions = []
            for term in search_terms:
                term_pattern = f"%{term}%"
                search_conditions.append(
                    or_(
                        Debate.title.ilike(term_pattern),
                        Debate.description.ilike(term_pattern)
                    )
                )
            if search_conditions:
                query = query.filter(*search_conditions)

        # 状态筛选
        if status and status.strip():
            try:
                status_enum = DebateStatus(status.strip().lower())
                query = query.filter(Debate.status == status_enum)
            except ValueError:
                pass  # 忽略无效状态

        # 排序
        sort_column = Debate.order  # 默认按order排序
        if sort_by == "created_at":
            sort_column = Debate.created_at
        elif sort_by == "title":
            sort_column = Debate.title

        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # 分页
        total = query.count()
        debates = query.offset((page - 1) * limit).limit(limit).all()

        # 转换为响应格式
        debate_list = [DebateResponse.model_validate(
            debate) for debate in debates]

        return {
            "items": debate_list,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit) if limit > 0 else 0
        }

    def create_debate(
        self,
        activity_id: str,
        debate_data: DebateCreate
    ) -> DebateResponse:
        """创建辩题

        Args:
            activity_id: 活动ID
            debate_data: 辩题数据

        Returns:
            创建的辩题
        """
        # 获取当前最大order值
        max_order = self.db.query(func.max(Debate.order)).filter(
            Debate.activity_id == activity_id
        ).scalar() or 0

        # 创建辩题
        debate_dict = debate_data.model_dump()
        debate = Debate(
            **debate_dict,
            activity_id=activity_id,
            order=max_order + 1
        )

        self.db.add(debate)
        self.db.commit()
        self.db.refresh(debate)

        return DebateResponse.model_validate(debate)

    def get_debate_by_id(self, debate_id: str) -> Debate:
        """获取辩题（内部使用）

        Args:
            debate_id: 辩题ID

        Returns:
            辩题对象

        Raises:
            HTTPException: 辩题不存在
        """
        debate = self.db.query(Debate).filter(Debate.id == debate_id).first()
        if not debate:
            raise HTTPException(status_code=404, detail="Debate not found")
        return debate

    def get_debate_detail(self, debate_id: str) -> DebateDetailResponse:
        """获取辩题详情（包含投票统计）

        Args:
            debate_id: 辩题ID

        Returns:
            辩题详情
        """
        debate = self.get_debate_by_id(debate_id)

        # 获取投票统计
        vote_stats = self.get_debate_vote_stats(debate_id)

        # 构建响应
        debate_dict = DebateResponse.model_validate(debate).model_dump()
        debate_detail = DebateDetailResponse(
            **debate_dict,
            vote_stats=vote_stats
        )

        return debate_detail

    def update_debate(
        self,
        debate_id: str,
        debate_data: DebateUpdate
    ) -> None:
        """更新辩题

        Args:
            debate_id: 辩题ID
            debate_data: 更新数据
        """
        debate = self.get_debate_by_id(debate_id)

        # 更新字段
        update_data = debate_data.model_dump(exclude_unset=True)

        if update_data:
            for field, value in update_data.items():
                if hasattr(debate, field):
                    self.db.query(Debate).filter(
                        Debate.id == debate_id
                    ).update({field: value})

        self.db.commit()

        # 如果更新了activity_id或status,清除Redis缓存
        if 'activity_id' in update_data or 'status' in update_data:
            from src.services.vote_service import VoteService
            service = VoteService(self.db)
            service.invalidate_debate_cache(debate_id)

    def update_debate_stages(
        self,
        debate_id: str,
        stages: list
    ) -> None:
        """更新辩题阶段设置

        Args:
            debate_id: 辩题ID
            stages: 阶段列表
        """
        import json

        debate = self.get_debate_by_id(debate_id)

        # 将 Pydantic 模型列表转换为字典列表再序列化为 JSON
        stages_dict = [stage.model_dump(by_alias=True) for stage in stages]
        stages_json = json.dumps(stages_dict, ensure_ascii=False)

        # 更新阶段设置
        self.db.query(Debate).filter(
            Debate.id == debate_id
        ).update({"stages": stages_json})

        self.db.commit()

    def delete_debate(self, debate_id: str) -> None:
        """删除辩题

        Args:
            debate_id: 辩题ID
        """
        from src.models.activity import Activity

        debate = self.get_debate_by_id(debate_id)

        # 检查是否为当前辩题
        activity = self.db.query(Activity).filter(
            Activity.id == debate.activity_id
        ).first()

        if activity:
            current_debate_id = getattr(activity, 'current_debate_id')
            if current_debate_id and str(current_debate_id) == str(debate_id):
                # 清除当前辩题
                setattr(activity, 'current_debate_id', None)

        # 删除辩题
        self.db.delete(debate)
        self.db.commit()

    def update_debate_status(
        self,
        debate_id: str,
        status_data: DebateStatusUpdate
    ) -> None:
        """更新辩题状态

        Args:
            debate_id: 辩题ID
            status_data: 状态数据
        """
        debate = self.get_debate_by_id(debate_id)
        activity_id = str(debate.activity_id)
        old_status = debate.status

        # 更新状态
        setattr(debate, 'status', status_data.status)
        self.db.commit()

        # 如果是从pending转换到ongoing，需要处理未投票的参与者
        if str(old_status) == "pending" and str(status_data.status) == "ongoing":
            self._handle_pending_to_ongoing_transition(debate_id, activity_id)

        # 清除Redis缓存
        from src.services.vote_service import VoteService
        service = VoteService(self.db)
        service.invalidate_debate_cache(debate_id)

        # 触发统计更新和 WebSocket 广播（异步）
        import asyncio
        asyncio.create_task(
            self._trigger_statistics_update_after_status_change(activity_id, debate_id))

    def reorder_debates(self, reorder_data: DebateReorder) -> None:
        """调整辩题顺序

        Args:
            reorder_data: 排序数据
        """
        if not reorder_data.debates:
            raise HTTPException(status_code=400, detail="No debates provided")

        # 批量更新顺序
        for item in reorder_data.debates:
            self.db.query(Debate).filter(
                Debate.id == item.id
            ).update({"order": item.order})

        self.db.commit()

    def get_debate_vote_stats(self, debate_id: str) -> VoteStats:
        """获取辩题投票统计

        Args:
            debate_id: 辩题ID

        Returns:
            投票统计数据
        """
        # 分别统计各种投票数量
        total_votes = self.db.query(func.count(Vote.id)).filter(
            Vote.debate_id == debate_id
        ).scalar() or 0

        pro_votes = self.db.query(func.count(Vote.id)).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.pro
        ).scalar() or 0

        con_votes = self.db.query(func.count(Vote.id)).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.con
        ).scalar() or 0

        abstain_votes = self.db.query(func.count(Vote.id)).filter(
            Vote.debate_id == debate_id,
            Vote.position == VotePosition.abstain
        ).scalar() or 0

        # 计算初始票数：从VoteHistory中获取每个投票的第一个位置
        votes_with_history = self.db.query(Vote).filter(
            Vote.debate_id == debate_id
        ).all()

        pro_previous_votes = 0
        con_previous_votes = 0
        abstain_previous_votes = 0

        # 统计从各方到其他方的人数
        pro_to_con = 0
        pro_to_abstain = 0
        con_to_pro = 0
        con_to_abstain = 0
        abstain_to_pro = 0
        abstain_to_con = 0

        for vote in votes_with_history:
            # 获取该投票的最早历史记录
            first_history = self.db.query(VoteHistory).filter(
                VoteHistory.vote_id == vote.id
            ).order_by(VoteHistory.created_at.asc()).first()

            if first_history:
                # 使用历史记录中的第一个位置
                initial_position = getattr(first_history, 'new_position')
            else:
                # 没有历史记录，说明从未改过票，使用当前位置
                initial_position = getattr(vote, 'position')

            # 当前位置
            current_position = getattr(vote, 'position')

            # 统计初始票数
            if initial_position == VotePosition.pro:
                pro_previous_votes += 1
            elif initial_position == VotePosition.con:
                con_previous_votes += 1
            elif initial_position == VotePosition.abstain:
                abstain_previous_votes += 1

            # 统计转换情况（初始位置和当前位置不同）
            if initial_position != current_position:
                if initial_position == VotePosition.pro and current_position == VotePosition.con:
                    pro_to_con += 1
                elif initial_position == VotePosition.pro and current_position == VotePosition.abstain:
                    pro_to_abstain += 1
                elif initial_position == VotePosition.con and current_position == VotePosition.pro:
                    con_to_pro += 1
                elif initial_position == VotePosition.con and current_position == VotePosition.abstain:
                    con_to_abstain += 1
                elif initial_position == VotePosition.abstain and current_position == VotePosition.pro:
                    abstain_to_pro += 1
                elif initial_position == VotePosition.abstain and current_position == VotePosition.con:
                    abstain_to_con += 1

        # 计算弃权百分比
        abstain_percentage = (abstain_votes / total_votes *
                              100) if total_votes > 0 else 0

        # 计算正方和反方百分比
        pro_percentage = (pro_votes / total_votes *
                          100) if total_votes > 0 else 0
        con_percentage = (con_votes / total_votes *
                          100) if total_votes > 0 else 0

        # 计算得分（根据规则）
        # 正方得分 = 反方到正方人数/反方初始人数 * 1000 + 中立到正方人数/中立初始人数 * 500
        pro_score = 0.0
        if con_previous_votes > 0:
            pro_score += (con_to_pro / con_previous_votes * 1000)
        if abstain_previous_votes > 0:
            pro_score += (abstain_to_pro / abstain_previous_votes * 500)

        # 反方得分 = 正方到反方人数/正方初始人数 * 1000 + 中立到反方人数/中立初始人数 * 500
        con_score = 0.0
        if pro_previous_votes > 0:
            con_score += (pro_to_con / pro_previous_votes * 1000)
        if abstain_previous_votes > 0:
            con_score += (abstain_to_con / abstain_previous_votes * 500)

        return VoteStats(
            debateId=debate_id,
            totalVotes=total_votes,
            proVotes=pro_votes,
            conVotes=con_votes,
            abstainVotes=abstain_votes,
            abstainPercentage=round(abstain_percentage, 2),
            proPreviousVotes=pro_previous_votes,
            conPreviousVotes=con_previous_votes,
            abstainPreviousVotes=abstain_previous_votes,
            proToConVotes=pro_to_con,
            conToProVotes=con_to_pro,
            abstainToProVotes=abstain_to_pro,
            abstainToConVotes=abstain_to_con,
            proScore=round(pro_score, 2),
            conScore=round(con_score, 2),
            winner=None,
            isLocked=False,
            lockedAt=None
        )

    def get_current_debate(self, activity_id: str) -> DebateDetailResponse:
        """获取活动的当前辩题

        Args:
            activity_id: 活动ID

        Returns:
            当前辩题详情

        Raises:
            HTTPException: 活动不存在或未设置当前辩题
        """
        from src.models.activity import Activity

        activity = self.db.query(Activity).filter(
            Activity.id == activity_id
        ).first()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        current_debate_id = getattr(activity, 'current_debate_id')
        if not current_debate_id:
            raise HTTPException(
                status_code=404, detail="No current debate set")

        debate = self.db.query(Debate).filter(
            Debate.id == current_debate_id
        ).first()

        if not debate:
            raise HTTPException(
                status_code=404, detail="Current debate not found")

        # 获取投票统计
        vote_stats = self.get_debate_vote_stats(str(debate.id))

        # 构建响应
        debate_dict = DebateResponse.model_validate(debate).model_dump()
        debate_detail = DebateDetailResponse(
            **debate_dict,
            vote_stats=vote_stats
        )

        return debate_detail

    def set_current_debate(
        self,
        activity_id: str,
        debate_id: str
    ) -> None:
        """设置活动的当前辩题

        Args:
            activity_id: 活动ID
            debate_id: 辩题ID

        Raises:
            HTTPException: 辩题不存在或不属于该活动
        """
        from src.models.activity import Activity

        # 验证辩题是否存在且属于该活动
        debate = self.db.query(Debate).filter(
            Debate.id == debate_id,
            Debate.activity_id == activity_id
        ).first()

        if not debate:
            raise HTTPException(
                status_code=404,
                detail="Debate not found in this activity"
            )

        # 获取活动
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id
        ).first()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 将所有当前活动的辩题（状态为ongoing或final_vote）设置为ended
        self.db.query(Debate).filter(
            Debate.activity_id == activity_id,
            Debate.status.in_([DebateStatus.ongoing, DebateStatus.final_vote])
        ).update({
            "status": DebateStatus.ended,
            "ended_at": datetime.now()
        })

        # 如果新辩题已经是ended状态，将其重新激活为ongoing，并重置后续辩题为pending
        if getattr(debate, 'status', None) == DebateStatus.ended:
            # 将新辩题设为ongoing
            setattr(debate, 'status', DebateStatus.ongoing)
            # 重置后续辩题为pending
            self.db.query(Debate).filter(
                Debate.activity_id == activity_id,
                Debate.order > debate.order
            ).update({
                "status": DebateStatus.pending,
                "started_at": None,
                "ended_at": None
            })
        else:
            # 设置新辩题状态为ongoing
            setattr(debate, 'status', DebateStatus.ongoing)

        # 标记新辩题开始
        debate_started_at = getattr(debate, 'started_at', None)
        if not debate_started_at:
            setattr(debate, 'started_at', datetime.now())

        # 更新当前辩题
        self.db.query(Activity).filter(
            Activity.id == activity_id
        ).update({"current_debate_id": debate_id})

        self.db.commit()

        # 触发辩题切换广播和统计更新（异步）
        import asyncio
        asyncio.create_task(
            self._trigger_debate_change_broadcast(activity_id, debate_id))

    async def _trigger_debate_change_broadcast(self, activity_id: str, debate_id: str):
        """辩题切换后触发辩题切换广播和统计更新"""
        try:
            from src.core.database import SessionLocal
            from src.core.websocket_manager import broadcast_debate_change

            # 创建新的数据库会话用于异步任务
            db = SessionLocal()
            try:
                # 先获取统计服务实例，确保 stats_service 始终被绑定
                from src.services.statistics_service import get_statistics_service
                stats_service = get_statistics_service(db)

                # 获取辩题信息
                debate = db.query(Debate).filter(
                    Debate.id == debate_id).first()
                if debate:
                    # 构建辩题数据
                    debate_data = {
                        "id": str(debate.id),
                        "title": str(debate.title),
                        "proDescription": str(getattr(debate, 'pro_description', '') or ''),
                        "conDescription": str(getattr(debate, 'con_description', '') or ''),
                        "background": str(getattr(debate, 'background', '') or ''),
                        "status": str(debate.status.value) if hasattr(debate.status, 'value') else str(debate.status),
                        "order": debate.order,
                        "activityId": str(debate.activity_id)
                    }

                    # 广播辩题切换事件
                    await broadcast_debate_change(activity_id, debate_data)

                # 无论 debate 是否存在，都调用统计更新
                await stats_service.update_statistics_cache(activity_id, debate_id)

            finally:
                db.close()
        except Exception as e:
            print(f"[ERROR] 触发统计更新广播失败: {e}")

    def _handle_pending_to_ongoing_transition(self, debate_id: str, activity_id: str):
        """处理从pending到ongoing状态的转换

        对于所有在pending阶段没有投票的已入场参与者，
        在转换到ongoing时自动设置为abstain投票
        """
        try:
            from src.services.vote_service import VoteService
            from src.models.vote import Participant
            import json
            from datetime import datetime, timezone
            import uuid
            from src.core.redis import get_redis

            redis = get_redis()

            # 获取已入场但未对此辩题投票的参与者
            checked_in_participants = self.db.query(Participant).filter(
                Participant.activity_id == activity_id,
                Participant.checked_in == True
            ).all()

            # 获取已投票的参与者集合
            voted_participants_raw = redis.smembers(
                f"debate:{debate_id}:votes")  # type: ignore
            from typing import Set, cast
            voted_participants = cast(
                Set[str], voted_participants_raw) if voted_participants_raw else set()

            # 为未投票的参与者创建abstain票
            non_voted_count = 0
            for participant in checked_in_participants:
                participant_id = str(participant.id)
                if participant_id not in voted_participants:
                    non_voted_count += 1
                    # 创建abstain投票记录
                    vote_data = {
                        "vote_id": str(uuid.uuid4()),
                        "participant_id": participant_id,
                        "debate_id": debate_id,
                        "position": "abstain",
                        "change_count": 0,
                        "is_final": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }

                    # 存储到Redis
                    vote_key = f"vote:{debate_id}:{participant_id}"
                    redis.set(vote_key, json.dumps(vote_data))  # type: ignore

                    # 添加到投票者集合和位置集合
                    redis.sadd(f"debate:{debate_id}:votes",
                               participant_id)  # type: ignore
                    # type: ignore
                    redis.sadd(
                        f"debate:{debate_id}:position:abstain", participant_id)

            print(
                f"[INFO] 处理pending到ongoing转换完成，为{non_voted_count}个未投票参与者设置为abstain")

        except Exception as e:
            print(f"[ERROR] 处理pending到ongoing转换失败: {e}")

    async def _trigger_statistics_update_after_status_change(self, activity_id: str, debate_id: str):
        """辩题状态更新后触发统计更新和 WebSocket 广播"""
        try:
            from src.core.database import SessionLocal
            from src.services.statistics_service import get_statistics_service

            # 创建新的数据库会话用于异步任务
            db = SessionLocal()
            try:
                stats_service = get_statistics_service(db)
                # 更新统计缓存并广播（包含防抖逻辑）
                await stats_service.update_statistics_cache(activity_id, debate_id)
            finally:
                db.close()
        except Exception as e:
            print(f"[ERROR] 触发状态更新后的统计更新失败: {e}")
