from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.core.database import Base


class UserOauthAccount(Base):
    """OAuth / OIDC provider 账号绑定记录。

    为未来接入第三方登录（微信/支付宝/Google/GitHub 等）预留框架。
    一个用户可绑定多个 provider，同一 provider 同一 provider_user_id 全局唯一。
    """
    __tablename__ = "user_oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(32), nullable=False)          # wechat_mp / wechat_web / alipay / google / github
    provider_user_id = Column(String(128), nullable=False)  # openid / sub
    unionid = Column(String(128), nullable=True)            # 微信 unionid，跨应用
    access_token = Column(String(512), nullable=True)       # 预留
    refresh_token = Column(String(512), nullable=True)      # 预留
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 预留
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        Index("ix_oauth_unionid", "unionid"),
    )
