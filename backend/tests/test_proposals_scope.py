"""GET /proposals 的 scope=mine 过滤回归测试。

背景：管理员「我的提议」（MyProposalsView）与审核台（ProposalsView）共用
GET /proposals，后端按 is_admin 分流——管理员看全部。导致管理员在「我的提议」
页混入他人提交的 pending 提议（用户报告："我的提议"里出现了非管理员添加的内容）。

修复：加 scope=mine 强制按 proposer_id 过滤（无论角色）；不传时保持原行为
（管理员看全部、普通用户看自己），审核台向后兼容。
"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base
from app.models.change_proposal import ChangeProposal
from conftest import TestingSessionLocal, engine

api_client = TestClient(app)


def _seed_proposals():
    """插两条提议：admin(id=1) applied 一条、普通用户(id=2) pending 一条。返回 (admin_pid, user_pid)。"""
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    db.query(ChangeProposal).delete()
    db.commit()
    pa = ChangeProposal(entity_type="unit", entity_id=None, action="create",
                        payload={"name": "admin直写"}, review_policy="auto_approve",
                        risk_level="mid", status="applied", proposer_id=1, reviewer_id=1)
    pu = ChangeProposal(entity_type="unit", entity_id=None, action="create",
                        payload={"name": "用户提交"}, review_policy="manual",
                        risk_level="mid", status="pending", proposer_id=2)
    db.add_all([pa, pu]); db.commit()
    db.refresh(pa); db.refresh(pu)
    out = (pa.id, pu.id)
    db.close()
    return out


def test_admin_default_list_returns_all(as_admin):
    """管理员不带 scope → 全部（审核台语义，向后兼容）。"""
    admin_pid, user_pid = _seed_proposals()
    r = api_client.get("/api/v1/proposals")
    assert r.status_code == 200, r.text
    ids = {it["id"] for it in r.json()}
    assert ids == {admin_pid, user_pid}


def test_admin_scope_mine_excludes_others(as_admin):
    """管理员 scope=mine → 只看 proposer_id=自己（「我的提议」语义）。"""
    admin_pid, user_pid = _seed_proposals()
    r = api_client.get("/api/v1/proposals", params={"scope": "mine"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == admin_pid
    assert items[0]["proposer_id"] == 1


def test_non_admin_scope_mine_still_own_only(as_non_admin):
    """普通用户 scope=mine → 仍只看自己（与默认一致，不泄漏他人）。"""
    admin_pid, user_pid = _seed_proposals()
    r = api_client.get("/api/v1/proposals", params={"scope": "mine"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == user_pid
    assert items[0]["proposer_id"] == 2
