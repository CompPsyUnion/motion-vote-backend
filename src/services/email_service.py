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
您好！

您正在注册 Motion Vote 账号，您的验证码是：

{code}

此验证码将在 10 分钟后过期，请及时使用。

如果这不是您的操作，请忽略此邮件。

---
Motion Vote 团队
            """.strip()
        elif purpose == "reset_password":
            subject = "Motion Vote - 密码重置验证码"
            body = f"""
您好！

您正在重置 Motion Vote 账号密码，您的验证码是：

{code}

此验证码将在 10 分钟后过期，请及时使用。

如果这不是您的操作，请立即联系我们。

---
Motion Vote 团队
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
                        "body_type": "plain"
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
