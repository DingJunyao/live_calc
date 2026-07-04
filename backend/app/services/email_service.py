"""SMTP 邮件发送服务，异步（threading）发送不阻塞请求。"""
import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务。构造时传入 SmtpConfig ORM 对象或 None。"""

    def __init__(self, config: Optional["SmtpConfig"] = None):
        self._config = config

    @property
    def ready(self) -> bool:
        return self._config is not None and self._config.enabled and bool(self._config.host)

    def send_template_async(self, template_key: str, to_email: str, variables: dict, db) -> None:
        """根据模板 key 渲染并异步发送。静默跳过：服务未就绪、模板不存在。"""
        if not self.ready:
            logger.warning("邮件服务未就绪（enabled=%s host=%s），跳过发送",
                         self._config.enabled if self._config else "N/A",
                         self._config.host if self._config else "N/A")
            return
        from app.models.email_template import EmailTemplate
        template = db.query(EmailTemplate).filter(EmailTemplate.key == template_key).first()
        if not template:
            logger.warning("邮件模板 %s 不存在，跳过发送", template_key)
            return
        subject = Template(template.subject).safe_substitute(variables)
        body = Template(template.body_html).safe_substitute(variables)
        self._send_async(to_email, subject, body)

    def send_test_async(self, to_email: str) -> None:
        """发送测试邮件。"""
        self._send_async(to_email, "测试邮件 - LiveCalc",
                        "<h1>SMTP 配置测试</h1><p>这是一封测试邮件，来自 LiveCalc。如果收到此邮件，说明 SMTP 配置正确。</p>")

    def _send_async(self, to_email: str, subject: str, body_html: str) -> None:
        thread = threading.Thread(target=self._send_sync, args=(to_email, subject, body_html), daemon=True)
        thread.start()

    def _send_sync(self, to_email: str, subject: str, body_html: str) -> None:
        config = self._config
        if not config or not config.host:
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{config.from_name} <{config.from_address}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if config.use_tls:
                server = smtplib.SMTP(config.host, config.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(config.host, config.port, timeout=10)

            if config.username:
                server.login(config.username, config.password)
            server.sendmail(config.from_address, [to_email], msg.as_string())
            server.quit()
            logger.info("邮件发送成功: to=%s subject=%s", to_email, subject)
        except Exception as e:
            logger.error("邮件发送失败: to=%s subject=%s error=%s", to_email, subject, e)
