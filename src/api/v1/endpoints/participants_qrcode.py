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
            text_height = 120  # 大幅增加文本区域高度
            canvas = Image.new(
                'RGB', (qr_width, qr_height + text_height), 'white')
            canvas.paste(img, (0, 0))

            # 绘制文本 - 使用更大的字体尺寸
            draw = ImageDraw.Draw(canvas)
            
            # 准备文本内容
            text = f"编号: {participant.code}"
            if participant.name:
                text += f" | {participant.name}"

            # 尝试多种字体，确保找到可用的大字体
            font = None
            font_size = 48  # 起始字体大小
            font_paths = [
                "arial.ttf",
                "Arial.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
            
            # 如果找不到字体文件，使用PIL的默认字体但加粗渲染
            if font is None:
                font = ImageFont.load_default()
                # 使用默认字体时，多次绘制文本以产生加粗效果
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height_actual = bbox[3] - bbox[1]
                text_x = (qr_width - text_width) // 2
                text_y = qr_height + (text_height - text_height_actual) // 2
                
                # 多次绘制以加粗
                for offset_x in range(-2, 3):
                    for offset_y in range(-2, 3):
                        draw.text((text_x + offset_x, text_y + offset_y), text, fill='black', font=font)
            else:
                # 使用TrueType字体正常绘制
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height_actual = bbox[3] - bbox[1]
                
                # 如果文本太宽，尝试减小字体直到合适
                while text_width > qr_width - 20 and font_size > 20:
                    font_size -= 2
                    font = ImageFont.truetype(font_path, font_size)
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height_actual = bbox[3] - bbox[1]
                
                text_x = (qr_width - text_width) // 2
                text_y = qr_height + (text_height - text_height_actual) // 2
                
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
