"""
参与者二维码生成端点
"""
import io
import zipfile
from typing import List

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.core.database import get_db
from src.models.user import User
from src.models.vote import Participant

router = APIRouter()


@router.get("/participants/qrcode")
async def export_participants_qrcode(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    导出所有参与者的二维码
    生成每个参与者的入场二维码，打包为ZIP文件
    """
    # 查询活动
    from src.models.activity import Activity
    activity = db.query(Activity).filter(Activity.id == activity_id).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="活动不存在"
        )

    # 检查用户权限（是否为活动所有者或协作者）
    if activity.owner_id != current_user.id:
        # TODO: 检查是否为协作者
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限访问此活动"
        )

    # 获取所有参与者
    participants: List[Participant] = db.query(Participant).filter(
        Participant.activity_id == activity_id
    ).all()

    if not participants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该活动没有参与者"
        )

    # 创建内存中的ZIP文件
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for idx, participant in enumerate(participants):
            # 生成参与者入场URL（使用 participant.code）
            url = f"https://motionvote.ibuduan.com/participant?participantID={participant.code}"

            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # 创建二维码图片
            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为PIL Image以便进一步处理
            if not isinstance(img, Image.Image):
                img = img.convert('RGB')

            # 在图片下方添加参与者信息文本
            # 创建一个更大的画布来容纳二维码和文本
            qr_width, qr_height = img.size
            text_height = 80  # 增加文本区域高度
            canvas = Image.new(
                'RGB', (qr_width, qr_height + text_height), 'white')
            canvas.paste(img, (0, 0))

            # 绘制文本
            draw = ImageDraw.Draw(canvas)
            text = f"编号: {participant.code}"
            if participant.name:
                text += f" | {participant.name}"

            # 使用更大的字体，确保宽度与QR码等宽
            try:
                # 尝试使用更大的字体
                font = ImageFont.truetype("arial.ttf", 48)  # 从20增加到24
            except:
                # 如果没有找到字体，使用默认字体
                font = ImageFont.load_default()

            # 计算文本位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (qr_width - text_width) // 2
            text_y = qr_height + 20

            draw.text((text_x, text_y), text, fill='black', font=font)

            # 将图片保存到内存
            img_buffer = io.BytesIO()
            canvas.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            # 生成文件名（使用参与者编号和姓名）
            filename = f"{participant.code}"
            if participant.name:
                # 清理文件名中的特殊字符
                safe_name = "".join(
                    c for c in participant.name if c.isalnum() or c in (' ', '_', '-'))
                filename += f"_{safe_name}"
            filename += ".png"

            # 将图片添加到ZIP文件
            zip_file.writestr(filename, img_buffer.getvalue())

    # 重置ZIP缓冲区位置
    zip_buffer.seek(0)

    # 返回ZIP文件
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=participants_qrcode_{activity_id}.zip"
        }
    )
