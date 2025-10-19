import random
import string

import httpx
from src.config import settings


class EmailService:
    """邮件发送服务"""

    def __init__(self):
        self.smtp_service_url = settings.smtp_service_url
        self.api_key = settings.smtp_api_key

    def generate_verification_code(self, length: int = 6) -> str:
        """生成验证码"""
        return ''.join(random.choices(string.digits, k=length))

    async def send_verification_code(self, email: str, code: str, purpose: str = "register") -> dict:
        """发送验证码邮件"""

        # 根据用途生成不同的邮件内容
        if purpose == "register":
            subject = "Motion Vote - 注册验证码"
            body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: #333; margin-bottom: 20px; }}
        .content {{ color: #666; line-height: 1.6; }}
        .code-box {{ background-color: #f0f0f0; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0; font-size: 24px; font-weight: bold; text-align: center; color: #007bff; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Motion Vote 注册验证</h2>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>感谢您注册 Motion Vote 账号。请使用以下验证码完成注册：</p>
            <div class="code-box">{code}</div>
            <p>此验证码将在 <strong>10 分钟</strong>后过期，请及时使用。</p>
            <p>如果这不是您的操作，请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>© Motion Vote 团队</p>
        </div>
    </div>
</body>
</html>
            """.strip()
        elif purpose == "reset_password":
            subject = "Motion Vote - 密码重置验证码"
            body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: #333; margin-bottom: 20px; }}
        .content {{ color: #666; line-height: 1.6; }}
        .code-box {{ background-color: #f0f0f0; border-left: 4px solid #ff6b6b; padding: 15px; margin: 20px 0; font-size: 24px; font-weight: bold; text-align: center; color: #ff6b6b; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Motion Vote 密码重置验证</h2>
        </div>
        <div class="content">
            <p>您好！</p>
            <p>您正在重置 Motion Vote 账号密码。请使用以下验证码完成重置：</p>
            <div class="code-box">{code}</div>
            <p>此验证码将在 <strong>10 分钟</strong>后过期，请及时使用。</p>
            <p>如果这不是您的操作，请立即联系我们。</p>
        </div>
        <div class="footer">
            <p>© Motion Vote 团队</p>
        </div>
    </div>
</body>
</html>
            """.strip()
        else:
            subject = "Motion Vote - 验证码"
            body = f"您的验证码是：{code}，请在 10 分钟内使用。"

        # 发送邮件请求
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.smtp_service_url}/v1/mail/send",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": self.api_key
                    },
                    json={
                        "recipient_email": email,
                        "subject": subject,
                        "body": body,
                        "body_type": "html"  # 修改为 html 以正确渲染邮件内容
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "message": result.get("message", "邮件发送成功"),
                        "email_id": result.get("email_id")
                    }
                else:
                    return {
                        "success": False,
                        "message": f"邮件发送失败：{response.text}"
                    }

            except httpx.RequestError as e:
                return {
                    "success": False,
                    "message": f"邮件服务连接失败：{str(e)}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"邮件发送异常：{str(e)}"
                }
