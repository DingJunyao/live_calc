"""SMTP 邮件发送服务，异步（threading）发送不阻塞请求。"""
import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SmtpConfigData:
    """SMTP 配置的纯数据副本，避免后台线程持有 ORM 对象导致 session-detached 报错。"""
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    from_address: str = ""
    from_name: str = "LiveCalc"
    enabled: bool = False

    @classmethod
    def from_orm(cls, config) -> "SmtpConfigData":
        return cls(
            host=config.host or "",
            port=config.port or 587,
            username=config.username or "",
            password=config.password or "",
            use_tls=config.use_tls if config.use_tls is not None else True,
            use_ssl=config.use_ssl if config.use_ssl is not None else False,
            from_address=config.from_address or "",
            from_name=config.from_name or "LiveCalc",
            enabled=config.enabled if config.enabled is not None else False,
        )


class EmailService:
    """邮件服务。构造时传入 SmtpConfig ORM 对象或 SmtpConfigData，立即提取为纯数据。"""

    def __init__(self, config: Optional["SmtpConfig"] = None):
        if config is not None:
            self._cfg = config if isinstance(config, SmtpConfigData) else SmtpConfigData.from_orm(config)
        else:
            self._cfg = None

    @property
    def ready(self) -> bool:
        return self._cfg is not None and self._cfg.enabled and bool(self._cfg.host)

    def send_template_async(self, template_key: str, to_email: str, variables: dict, db) -> None:
        """根据模板 key 渲染并异步发送。静默跳过：服务未就绪、模板不存在。

        注意：template 的查询在调用线程 db session 内完成，渲染结果（纯字符串）传入后台线程。
        """
        if not self.ready:
            logger.warning("邮件服务未就绪（enabled=%s host=%s），跳过发送",
                         self._cfg.enabled if self._cfg else "N/A",
                         self._cfg.host if self._cfg else "N/A")
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
        cfg = self._cfg
        if not cfg or not cfg.host:
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{cfg.from_name} <{cfg.from_address}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if cfg.use_ssl:
                server = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=10)
            elif cfg.use_tls:
                server = smtplib.SMTP(cfg.host, cfg.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(cfg.host, cfg.port, timeout=10)

            if cfg.username:
                server.login(cfg.username, cfg.password)
            server.sendmail(cfg.from_address, [to_email], msg.as_string())
            server.quit()
            logger.info("邮件发送成功: to=%s subject=%s", to_email, subject)
        except Exception as e:
            logger.error("邮件发送失败: to=%s subject=%s error=%s", to_email, subject, e)
