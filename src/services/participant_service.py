import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy import and_
from sqlalchemy.orm import Session
from src.models.activity import Activity
from src.models.vote import Participant
from src.schemas.participant import (PaginatedParticipants,
                                     ParticipantBatchImportResult,
                                     ParticipantCreate, ParticipantResponse)


class ParticipantService:
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

    def get_participants_paginated(
        self,
        activity_id: str,
        user_id: str,
        page: int = 1,
        limit: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None,
        name: Optional[str] = None,
        code: Optional[str] = None,
        phone: Optional[str] = None,
        note: Optional[str] = None,
        checked_in: Optional[bool] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc"
    ) -> PaginatedParticipants:
        """获取分页参与者列表"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)

        # 构建查询
        query = self.db.query(Participant).filter(
            Participant.activity_id == activity_id)

        # 状态筛选（向后兼容）
        if status == "checked_in":
            query = query.filter(Participant.checked_in == True)
        elif status == "not_checked_in":
            query = query.filter(Participant.checked_in == False)

        # 入场状态筛选（新方式）
        if checked_in is not None:
            query = query.filter(Participant.checked_in == checked_in)

        # 全文搜索
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                Participant.name.ilike(search_term) |
                Participant.code.ilike(search_term) |
                Participant.phone.ilike(search_term)
            )

        # 具体字段模糊匹配
        if name:
            query = query.filter(Participant.name.ilike(f"%{name}%"))

        if code:
            query = query.filter(Participant.code.ilike(f"%{code}%"))

        if phone:
            query = query.filter(Participant.phone.ilike(f"%{phone}%"))

        if note:
            query = query.filter(Participant.note.ilike(f"%{note}%"))

        # 排序
        if sort_by and hasattr(Participant, sort_by):
            sort_column = getattr(Participant, sort_by)
        else:
            sort_column = Participant.created_at

        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 计算总数
        total = query.count()

        # 分页
        offset = (page - 1) * limit
        participants = query.offset(offset).limit(limit).all()

        # 计算总页数
        total_pages = (total + limit - 1) // limit

        return PaginatedParticipants(
            items=[ParticipantResponse.model_validate(
                p) for p in participants],
            total=total,
            page=page,
            limit=limit,
            totalPages=total_pages
        )

    def create_participant(
        self,
        activity_id: str,
        participant_data: ParticipantCreate,
        user_id: str
    ) -> ParticipantResponse:
        """创建参与者"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)

        # 生成参与者编号
        code = self._generate_participant_code(activity_id)

        # 创建参与者
        participant = Participant(
            activity_id=activity_id,
            code=code,
            name=participant_data.name,
            phone=participant_data.phone,
            note=participant_data.note
        )

        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        return ParticipantResponse.model_validate(participant)

    def _generate_participant_code(self, activity_id: str) -> str:
        """生成参与者编号"""
        # 获取当前活动的参与者数量
        count = self.db.query(Participant).filter(
            Participant.activity_id == activity_id
        ).count()
        return f"{count + 1:04d}"  # 生成4位数字编号，如0001, 0002

    def batch_import_participants(
        self,
        activity_id: str,
        file: UploadFile,
        user_id: str
    ) -> ParticipantBatchImportResult:
        """批量导入参与者"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)

        # 读取Excel文件
        try:
            contents = file.file.read()
            workbook = load_workbook(io.BytesIO(contents))
            worksheet = workbook.active

            total = 0
            success = 0
            failed = 0
            errors = []

            if worksheet is not None:
                # 跳过标题行，从第二行开始
                for row in worksheet.iter_rows(min_row=2, values_only=True):
                    if not row or not any(row):  # 跳过空行
                        continue

                    total += 1
                    try:
                        # 获取行数据
                        name = str(row[0]).strip() if row[0] else ""
                        phone = str(row[1]).strip() if len(
                            row) > 1 and row[1] else None
                        note = str(row[2]).strip() if len(
                            row) > 2 and row[2] else None

                        # 验证必填字段
                        if not name:
                            errors.append(f"第{total + 1}行：姓名不能为空")
                            failed += 1
                            continue

                        # 检查姓名是否已存在
                        existing = self.db.query(Participant).filter(
                            and_(
                                Participant.activity_id == activity_id,
                                Participant.name == name
                            )
                        ).first()

                        if existing:
                            errors.append(f"第{total + 1}行：参与者 {name} 已存在")
                            failed += 1
                            continue

                        # 创建参与者
                        code = self._generate_participant_code(activity_id)
                        participant = Participant(
                            activity_id=activity_id,
                            code=code,
                            name=name,
                            phone=phone,
                            note=note
                        )

                        self.db.add(participant)
                        success += 1

                    except Exception as e:
                        errors.append(f"第{total + 1}行：{str(e)}")
                        failed += 1

                # 提交所有更改
                if success > 0:
                    self.db.commit()

            return ParticipantBatchImportResult(
                total=total,
                success=success,
                failed=failed,
                errors=errors[:10]  # 只返回前10个错误
            )

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"文件处理错误: {str(e)}")

    def export_participants(self, activity_id: str, user_id: str) -> bytes:
        """导出参与者数据为CSV"""
        # 检查权限
        activity = self._check_activity_permission(activity_id, user_id)

        # 获取参与者数据
        participants = self.db.query(Participant).filter(
            Participant.activity_id == activity_id
        ).order_by(Participant.code).all()

        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # 写入标题行
        headers = ["编号", "姓名", "手机号", "备注", "是否入场", "入场时间", "创建时间"]
        writer.writerow(headers)

        # 写入数据行
        for participant in participants:
            # 处理手机号
            phone_value = getattr(participant, 'phone') or ""

            # 处理备注
            note_value = getattr(participant, 'note') or ""

            # 处理入场状态
            checked_in_value = getattr(participant, 'checked_in', False)
            checked_in_text = "是" if checked_in_value else "否"

            # 处理入场时间
            checked_in_at_value = getattr(participant, 'checked_in_at', None)
            if checked_in_at_value:
                checkin_time = checked_in_at_value.strftime(
                    "%Y-%m-%d %H:%M:%S")
            else:
                checkin_time = ""

            # 处理创建时间
            created_at_value = getattr(participant, 'created_at', None)
            if created_at_value:
                created_time = created_at_value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_time = ""

            # 写入行数据
            writer.writerow([
                str(participant.code),
                str(participant.name),
                str(phone_value),
                str(note_value),
                checked_in_text,
                checkin_time,
                created_time
            ])

        # 转换为字节
        csv_content = output.getvalue()
        output.close()

        # 添加BOM以确保Excel正确显示中文
        return '\ufeff'.encode('utf-8') + csv_content.encode('utf-8')

    def generate_participant_link(self, participant_id: str, user_id: str) -> dict:
        """生成参与者链接参数

        返回参与者的活动ID和编号，用于前端构建链接
        """
        participant = self.db.query(Participant).filter(
            Participant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="参与者不存在")

        # 检查权限
        self._check_activity_permission(str(participant.activity_id), user_id)

        return {
            "activityId": str(participant.activity_id),
            "participantCode": str(participant.code)
        }

    def generate_participant_qrcode(self, participant_id: str, user_id: str) -> bytes:
        """生成参与者二维码（简化版本）"""
        # 简化实现，返回空字节
        return b"QR code generation not implemented yet"

    def participant_enter(
        self,
        activity_id: str,
        participant_code: str,
        device_fingerprint: Optional[str] = None
    ) -> tuple[dict, dict]:
        """参与者入场"""
        # 查找参与者
        participant = self.db.query(Participant).filter(
            and_(
                Participant.activity_id == activity_id,
                Participant.code == participant_code
            )
        ).first()

        if not participant:
            raise HTTPException(status_code=404, detail="参与者不存在或编号错误")

        # 更新入场状态（简化实现）
        # 注意：这里不直接修改SQLAlchemy对象的属性，而是使用update方法
        self.db.query(Participant).filter(Participant.id == participant.id).update({
            "checked_in": True,
            "checked_in_at": datetime.now(timezone.utc),
            "device_fingerprint": device_fingerprint
        })
        self.db.commit()

        # 获取活动信息
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()

        activity_info = {
            "activity": {
                "id": str(activity.id) if activity else "",
                "name": str(activity.name) if activity else "",
                "status": activity.status.value if activity else "unknown",
                "current_debate": None  # TODO: 获取当前辩题
            },
            "participant": {
                "id": str(participant.id),
                "code": str(participant.code),
                "name": str(participant.name)
            }
        }

        vote_status = {
            "has_voted": False,  # TODO: 检查投票状态
            "position": None,
            "voted_at": None,
            "remaining_changes": 3,  # TODO: 从设置中获取
            "can_vote": True,
            "can_change": True
        }

        return activity_info, vote_status
