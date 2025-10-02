"""统计数据服务"""

import csv
import io
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session
from src.models.activity import Activity
from src.models.debate import Debate
from src.models.vote import Participant, Vote
from src.schemas.statistics import (ActivityReport, ActivitySummary,
                                    ActivityType, DashboardData, DebateResult,
                                    DebateStats, ExportType, RealTimeStats,
                                    RecentActivity, TimelinePoint, VoteResults)


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def _check_activity_permission(self, activity_id: str, user_id: str) -> Activity:
        """检查用户对活动的权限"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 检查是否是活动拥有者或协作者（简化检查）
        if str(activity.owner_id) != str(user_id):
            # TODO: 检查是否是协作者
            pass

        return activity

    def get_dashboard_data(self, activity_id: str, user_id: str) -> DashboardData:
        """获取实时数据看板"""
        # 检查权限
        activity = self._check_activity_permission(activity_id, user_id)

        # 获取实时统计数据
        real_time_stats = self._get_real_time_stats(activity_id)

        # 获取辩题统计
        debate_stats = self._get_debate_stats(activity_id)

        # 获取最近活动
        recent_activity = self._get_recent_activity(activity_id)

        # 获取当前辩题
        current_debate = None
        if hasattr(activity, 'current_debate_id') and activity.current_debate_id is not None:
            debate = self.db.query(Debate).filter(
                Debate.id == activity.current_debate_id).first()
            current_debate = str(debate.title) if debate else None

        return DashboardData(
            activityId=str(activity.id),
            activityName=str(activity.name),
            activityStatus=str(activity.status.value),
            currentDebate=current_debate,
            realTimeStats=real_time_stats,
            debateStats=debate_stats,
            recentActivity=recent_activity
        )

    def _get_real_time_stats(self, activity_id: str) -> RealTimeStats:
        """获取实时统计数据"""
        # 总参与人数
        total_participants = self.db.query(Participant).filter(
            Participant.activity_id == activity_id
        ).count()

        # 已入场人数
        checked_in_participants = self.db.query(Participant).filter(
            and_(
                Participant.activity_id == activity_id,
                Participant.checked_in == True
            )
        ).count()

        # 在线人数（简化：等于已入场人数）
        online_participants = checked_in_participants

        # 总投票数
        total_votes = self.db.query(Vote).join(
            Participant, Vote.participant_id == Participant.id
        ).filter(Participant.activity_id == activity_id).count()

        # 投票率
        vote_rate = 0.0
        if checked_in_participants > 0:
            # 获取当前辩题的投票数
            current_debate_votes = self.db.query(Vote).join(
                Participant, Vote.participant_id == Participant.id
            ).join(
                Debate, Vote.debate_id == Debate.id
            ).filter(
                and_(
                    Participant.activity_id == activity_id,
                    Debate.activity_id == activity_id,
                    Debate.status == 'ongoing'
                )
            ).count()

            vote_rate = round(current_debate_votes /
                              checked_in_participants * 100, 2)

        return RealTimeStats(
            totalParticipants=total_participants,
            checkedInParticipants=checked_in_participants,
            onlineParticipants=online_participants,
            totalVotes=total_votes,
            voteRate=vote_rate
        )

    def _get_debate_stats(self, activity_id: str) -> List[DebateStats]:
        """获取辩题统计"""
        debates = self.db.query(Debate).filter(
            Debate.activity_id == activity_id
        ).order_by(Debate.order).all()

        stats = []
        for debate in debates:
            vote_results = self._get_vote_results(str(debate.id))

            # 计算投票率
            checked_in_count = self.db.query(Participant).filter(
                and_(
                    Participant.activity_id == activity_id,
                    Participant.checked_in == True
                )
            ).count()

            vote_rate = 0.0
            if checked_in_count > 0:
                vote_rate = round(vote_results.total_votes /
                                  checked_in_count * 100, 2)

            stats.append(DebateStats(
                debateId=str(debate.id),
                debateTitle=str(debate.title),
                voteResults=vote_results,
                voteRate=vote_rate
            ))

        return stats

    def _get_vote_results(self, debate_id: str) -> VoteResults:
        """获取投票结果"""
        # 统计各立场的票数
        vote_counts = self.db.query(
            Vote.position,
            func.count(Vote.id).label('count')
        ).filter(Vote.debate_id == debate_id).group_by(Vote.position).all()

        pro_votes = 0
        con_votes = 0
        abstain_votes = 0

        for position, count in vote_counts:
            if position == 'pro':
                pro_votes = count
            elif position == 'con':
                con_votes = count
            elif position == 'abstain':
                abstain_votes = count

        total_votes = pro_votes + con_votes + abstain_votes

        return VoteResults(
            proVotes=pro_votes,
            conVotes=con_votes,
            abstainVotes=abstain_votes,
            totalVotes=total_votes
        )

    def _get_recent_activity(self, activity_id: str, limit: int = 10) -> List[RecentActivity]:
        """获取最近活动"""
        # 这里是简化实现，实际应该从活动日志表获取
        activities = []

        # 获取最近的投票活动
        recent_votes = self.db.query(Vote).join(
            Participant, Vote.participant_id == Participant.id
        ).filter(Participant.activity_id == activity_id).order_by(
            desc(Vote.created_at)
        ).limit(limit).all()

        for vote in recent_votes:
            participant = self.db.query(Participant).filter(
                Participant.id == vote.participant_id
            ).first()
            debate = self.db.query(Debate).filter(
                Debate.id == vote.debate_id
            ).first()

            if participant and debate:
                activities.append(RecentActivity(
                    type=ActivityType.VOTE_CAST,
                    timestamp=getattr(vote, 'created_at', datetime.min) if getattr(
                        vote, 'created_at', None) is not None else datetime.min,
                    description=f"参与者 {participant.code} 对辩题「{debate.title}」投票：{vote.position}"
                ))

        return sorted(activities, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_activity_report(self, activity_id: str, user_id: str) -> ActivityReport:
        """获取活动报告"""
        # 检查权限
        activity = self._check_activity_permission(activity_id, user_id)

        # 获取活动摘要
        summary = self._get_activity_summary(activity_id)

        # 获取辩题结果
        debate_results = self._get_debate_results(activity_id)

        return ActivityReport(
            activityId=str(activity.id),
            activityName=str(activity.name),
            createdAt=getattr(activity, 'created_at', datetime.min) if getattr(
                activity, 'created_at', None) is not None else datetime.min,
            startedAt=getattr(activity, 'start_time', None),
            endedAt=getattr(activity, 'end_time', None),
            summary=summary,
            debateResults=debate_results,
            generatedAt=datetime.now(timezone.utc)
        )

    def _get_activity_summary(self, activity_id: str) -> ActivitySummary:
        """获取活动摘要"""
        # 总参与人数
        total_participants = self.db.query(Participant).filter(
            Participant.activity_id == activity_id
        ).count()

        # 总投票数
        total_votes = self.db.query(Vote).join(
            Participant, Vote.participant_id == Participant.id
        ).filter(Participant.activity_id == activity_id).count()

        # 辩题总数
        total_debates = self.db.query(Debate).filter(
            Debate.activity_id == activity_id
        ).count()

        # 平均投票率
        average_vote_rate = 0.0
        if total_participants > 0 and total_debates > 0:
            average_vote_rate = round(
                total_votes / (total_participants * total_debates) * 100, 2)

        # 活动时长
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        duration = 0
        if activity and hasattr(activity, 'start_time') and hasattr(activity, 'end_time'):
            if activity.start_time is not None and activity.end_time is not None:
                # 注意：这里使用计划时间，而不是实际执行时间
                duration = int(
                    (activity.end_time - activity.start_time).total_seconds() / 60)

        return ActivitySummary(
            totalParticipants=total_participants,
            totalVotes=total_votes,
            totalDebates=total_debates,
            averageVoteRate=average_vote_rate,
            duration=duration
        )

    def _get_debate_results(self, activity_id: str) -> List[DebateResult]:
        """获取辩题结果"""
        debates = self.db.query(Debate).filter(
            Debate.activity_id == activity_id
        ).order_by(Debate.order).all()

        results = []
        for debate in debates:
            vote_results = self._get_vote_results(str(debate.id))
            timeline = self._get_debate_timeline(str(debate.id))

            # 计算辩题持续时间
            # TODO: 辩题模型中没有started_at和ended_at字段，使用预估时长
            duration = 0
            if hasattr(debate, 'estimated_duration') and debate.estimated_duration is not None:
                # If estimated_duration is a SQLAlchemy Column, get its value
                if hasattr(debate.estimated_duration, 'value'):
                    duration = debate.estimated_duration.value
                else:
                    duration = debate.estimated_duration

            results.append(DebateResult(
                debateId=str(debate.id),
                debateTitle=str(debate.title),
                debateOrder=int(getattr(debate, "order", 0)),
                results=vote_results,
                timeline=timeline,
                duration=int(duration) if isinstance(
                    duration, (int, float, str)) else 0
            ))

        return results

    def _get_debate_timeline(self, debate_id: str) -> List[TimelinePoint]:
        """获取辩题投票时间线"""
        # 简化实现：获取投票时间点
        votes = self.db.query(Vote).filter(
            Vote.debate_id == debate_id
        ).order_by(Vote.created_at).all()

        timeline = []
        pro_count = 0
        con_count = 0
        abstain_count = 0

        for vote in votes:
            if getattr(vote, 'position', None) == 'pro':
                pro_count += 1
            elif getattr(vote, 'position', None) == 'con':
                con_count += 1
            elif getattr(vote, 'position', None) == 'abstain':
                abstain_count += 1

            timeline.append(TimelinePoint(
                timestamp=getattr(vote, 'created_at', datetime.min) if getattr(
                    vote, 'created_at', None) is not None else datetime.min,
                proVotes=pro_count,
                conVotes=con_count,
                abstainVotes=abstain_count
            ))

        return timeline

    def export_data(self, activity_id: str, user_id: str, export_type: ExportType = ExportType.ALL) -> bytes:
        """导出原始数据为CSV格式"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)

        if export_type == ExportType.VOTES or export_type == ExportType.ALL:
            return self._export_votes_csv(activity_id)
        elif export_type == ExportType.CHANGES:
            return self._export_changes_csv(activity_id)
        elif export_type == ExportType.TIMELINE:
            return self._export_timeline_csv(activity_id)
        else:
            return self._export_all_csv(activity_id)

    def _export_votes_csv(self, activity_id: str) -> bytes:
        """导出投票数据为CSV"""
        # 获取投票数据
        votes_query = self.db.query(
            Participant.code.label('participant_code'),
            Participant.name.label('participant_name'),
            Debate.title.label('debate_title'),
            Debate.order.label('debate_order'),
            Vote.position,
            Vote.created_at.label('vote_time'),
            Vote.updated_at.label('last_updated')
        ).join(
            Participant, Vote.participant_id == Participant.id
        ).join(
            Debate, Vote.debate_id == Debate.id
        ).filter(
            Participant.activity_id == activity_id
        ).order_by(Vote.created_at)

        # 创建CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            '参与者编号', '参与者姓名', '辩题标题', '辩题顺序',
            '投票立场', '投票时间', '最后更新时间'
        ])

        # 写入数据
        for vote in votes_query.all():
            position_map = {
                'pro': '正方',
                'con': '反方',
                'abstain': '弃权'
            }

            writer.writerow([
                vote.participant_code,
                vote.participant_name,
                vote.debate_title,
                vote.debate_order,
                position_map.get(vote.position, vote.position),
                vote.vote_time.strftime(
                    '%Y-%m-%d %H:%M:%S') if vote.vote_time else '',
                vote.last_updated.strftime(
                    '%Y-%m-%d %H:%M:%S') if vote.last_updated else ''
            ])

        # 添加BOM以确保Excel正确显示中文
        csv_content = output.getvalue()
        output.close()

        return '\ufeff'.encode('utf-8') + csv_content.encode('utf-8')

    def _export_changes_csv(self, activity_id: str) -> bytes:
        """导出投票变更记录为CSV（简化实现）"""
        # 这里应该从投票变更日志表获取数据，目前简化处理
        return self._export_votes_csv(activity_id)

    def _export_timeline_csv(self, activity_id: str) -> bytes:
        """导出时间线数据为CSV"""
        # 获取所有辩题的时间线数据
        debates = self.db.query(Debate).filter(
            Debate.activity_id == activity_id
        ).order_by(Debate.order).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            '辩题标题', '辩题顺序', '时间点', '正方票数', '反方票数', '弃权票数', '总票数'
        ])

        for debate in debates:
            timeline = self._get_debate_timeline(str(debate.id))
            for point in timeline:
                total = point.pro_votes + point.con_votes + point.abstain_votes
                writer.writerow([
                    debate.title,
                    debate.order,
                    point.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    point.pro_votes,
                    point.con_votes,
                    point.abstain_votes,
                    total
                ])

        csv_content = output.getvalue()
        output.close()

        return '\ufeff'.encode('utf-8') + csv_content.encode('utf-8')

    def _export_all_csv(self, activity_id: str) -> bytes:
        """导出所有数据为CSV"""
        # 简化实现：返回投票数据
        return self._export_votes_csv(activity_id)
