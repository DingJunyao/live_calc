"""端到端生命周期验证：实体单位覆盖/密度 接入提议-审核框架的完整链路。

覆盖四个阶段（独立于单 task 单元测试，验证完整生命周期）：
  (a) 普通用户提交 → 待审（pending，列表无新数据）
  (b) 管理员审核通过 → 生效（applied，列表出现）
  (c) 管理员回滚 → 还原（reverted，create 提议数据消失 / delete 提议数据复活）
  (d) 下游不受 pending 影响（换算服务读不到待审数据；applied 后能读到）

实现要点：单测试内不在两个 Depends 身份 fixture 间切换（后者会覆盖前者）。
普通用户走 TestClient API（as_non_admin）；管理员审核/回滚直接调
proposal_service 服务层（经 db_session，与 client 共享同一内存库 StaticPool），
模拟管理员操作且避免 fixture 冲突。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.change_proposal import ChangeProposal
from app.models.entity_density import EntityDensity
from app.models.entity_unit_override import EntityUnitOverride
from app.services.proposals import service as proposal_service
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


class _AdminActor:
    """占位管理员对象，满足 proposal_service.review/revert 的 reviewer 参数。"""
    id = 1
    is_admin = True


@pytest.fixture(autouse=True)
def _setup():
    """TestClient 不触发 main.py lifespan，需显式注册执行器（全 manual）。"""
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _ingredient(db_session, name: str) -> int:
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


# ============ (a)(b)(c) 覆盖：create 提议完整生命周期 ============

def test_override_create_full_lifecycle(db_session, as_non_admin):
    """普通用户提交 create → 管理员审核通过生效 → 管理员回滚还原（数据消失）。

    普通用户走 client（as_non_admin）；审核/回滚经 proposal_service 服务层
    （db_session 与 client 共享内存库）模拟管理员。
    """
    ing_id = _ingredient(db_session, "e2e_覆盖_create")

    # (a) 普通用户提交 create
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒12", "weight_per_unit": 55.5},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 0  # 占位骨架，待审

    # change_proposals 表有 pending 记录
    prop = (
        db_session.query(ChangeProposal)
        .filter(
            ChangeProposal.entity_type == "entity_unit_override",
            ChangeProposal.action == "create",
        )
        .order_by(ChangeProposal.id.desc())
        .first()
    )
    assert prop is not None
    assert prop.status == "pending"
    assert prop.payload["unit_name"] == "盒12"
    proposal_id = prop.id

    # 列表无新数据（待审未生效）
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["unit_name"] != "盒12" for u in lst)

    # (b) 管理员审核通过 → 生效（服务层，模拟管理员）
    proposal_service.review(db_session, proposal_id=proposal_id,
                            approved=True, reviewer=_AdminActor(), note="e2e 通过")
    db_session.commit()
    db_session.expire_all()

    prop_after = db_session.query(ChangeProposal).get(proposal_id)
    assert prop_after.status == "applied"

    # 覆盖数据出现（is_active=True）
    override = (
        db_session.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.entity_type == "ingredient",
            EntityUnitOverride.entity_id == ing_id,
            EntityUnitOverride.unit_name == "盒12",
            EntityUnitOverride.is_active.is_(True),
        )
        .first()
    )
    assert override is not None
    assert float(override.weight_per_unit) == 55.5

    # 列表能看到
    lst2 = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert any(u["unit_name"] == "盒12" for u in lst2)

    # (c) 管理员回滚 → 还原（create 提议：新建行被删除）
    proposal_service.revert(db_session, proposal_id=proposal_id, reviewer=_AdminActor())
    db_session.commit()
    db_session.expire_all()

    prop_final = db_session.query(ChangeProposal).get(proposal_id)
    assert prop_final.status == "reverted"

    override_after = (
        db_session.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.entity_type == "ingredient",
            EntityUnitOverride.entity_id == ing_id,
            EntityUnitOverride.unit_name == "盒12",
        )
        .first()
    )
    assert override_after is None  # create 回滚 = 硬删新建行

    # 列表不再有
    lst3 = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["unit_name"] != "盒12" for u in lst3)


# ============ (a)(b)(c) 覆盖：delete 提议回滚复活 ============

def test_override_delete_revert_revives(db_session, as_admin):
    """delete 提议：管理员直写软删 → 回滚复活（is_active 恢复 True）。"""
    ing_id = _ingredient(db_session, "e2e_覆盖_delete")
    # 管理员直接建一条覆盖（apply_as_admin 立即生效）
    create_resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "袋", "weight_per_unit": 30},
    )
    assert create_resp.status_code == 201
    oid = create_resp.json()["id"]
    assert oid != 0

    # 管理员提交 delete 提议（apply_as_admin 立即软删）
    del_resp = client.delete(f"/api/v1/entities/ingredient/{ing_id}/units/{oid}")
    assert del_resp.status_code == 200

    # 列表已无（软删生效）
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["id"] != oid for u in lst)

    # 找到 delete 提议（applied）
    prop = (
        db_session.query(ChangeProposal)
        .filter(
            ChangeProposal.entity_type == "entity_unit_override",
            ChangeProposal.action == "delete",
            ChangeProposal.entity_id == oid,
        )
        .order_by(ChangeProposal.id.desc())
        .first()
    )
    assert prop is not None
    assert prop.status == "applied"

    # 回滚 → 复活（服务层，模拟管理员）
    proposal_service.revert(db_session, proposal_id=prop.id, reviewer=_AdminActor())
    db_session.commit()
    db_session.expire_all()

    revived = db_session.query(EntityUnitOverride).get(oid)
    assert revived.is_active in (True, 1)  # 复活

    lst2 = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert any(u["id"] == oid for u in lst2)


# ============ (a)(b)(c) 密度：create 提议完整生命周期 ============

def test_density_create_full_lifecycle(db_session, as_non_admin):
    """普通用户提交密度 create → 管理员审核通过 → 管理员回滚。"""
    ing_id = _ingredient(db_session, "e2e_密度_create")

    # (a) 普通用户提交
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/density",
        json={"density": 780, "source": "e2e 估测"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == 0  # 占位

    prop = (
        db_session.query(ChangeProposal)
        .filter(
            ChangeProposal.entity_type == "entity_density",
            ChangeProposal.action == "create",
        )
        .order_by(ChangeProposal.id.desc())
        .first()
    )
    assert prop is not None
    assert prop.status == "pending"
    assert float(prop.payload["density"]) == 780.0
    proposal_id = prop.id

    # 待审：列表无
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/density").json()
    assert all(not (abs(float(d["density"]) - 780.0) < 0.01) for d in lst)

    # (b) 管理员审核通过
    proposal_service.review(db_session, proposal_id=proposal_id,
                            approved=True, reviewer=_AdminActor(), note="e2e 密度通过")
    db_session.commit()
    db_session.expire_all()

    dens = (
        db_session.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == "ingredient",
            EntityDensity.entity_id == ing_id,
            EntityDensity.is_active.is_(True),
        )
        .first()
    )
    assert dens is not None
    assert abs(float(dens.density) - 780.0) < 0.01

    # (c) 管理员回滚
    proposal_service.revert(db_session, proposal_id=proposal_id, reviewer=_AdminActor())
    db_session.commit()
    db_session.expire_all()

    dens_after = (
        db_session.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == "ingredient",
            EntityDensity.entity_id == ing_id,
        )
        .first()
    )
    assert dens_after is None  # create 回滚 = 删除新建行


# ============ (d) 下游不受 pending 影响 ============

def test_downstream_pending_then_applied(db_session, as_non_admin):
    """换算服务：pending 期间读不到待审数据；applied 后能用到新覆盖。

    用 /api/v1/units/convert 端点（经 UnitConversionService）验证下游读取：
    创建一个 weight_per_unit=100 的覆盖提议前，换算 1 盒d→g 应失败（无覆盖）；
    管理员审核通过后，1 盒d→g 应 = 100g。
    """
    ing_id = _ingredient(db_session, "e2e_下游")

    # pending 前：1 盒d→g 无法换算（无覆盖）→ convert 返回 400
    r0 = client.post(
        "/api/v1/units/convert",
        json={"value": 1, "from_unit": "盒d", "to_unit": "g",
              "entity_type": "ingredient", "entity_id": ing_id},
    )
    assert r0.status_code == 400  # 不支持

    # 普通用户提交覆盖提议（待审）
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒d", "weight_per_unit": 100},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 0

    prop = (
        db_session.query(ChangeProposal)
        .filter(
            ChangeProposal.entity_type == "entity_unit_override",
            ChangeProposal.action == "create",
        )
        .order_by(ChangeProposal.id.desc())
        .first()
    )
    assert prop.status == "pending"

    # pending 期间：换算仍失败（读不到待审数据）
    r1 = client.post(
        "/api/v1/units/convert",
        json={"value": 1, "from_unit": "盒d", "to_unit": "g",
              "entity_type": "ingredient", "entity_id": ing_id},
    )
    assert r1.status_code == 400  # 下游未受 pending 影响

    # 管理员审核通过（服务层）
    proposal_service.review(db_session, proposal_id=prop.id,
                            approved=True, reviewer=_AdminActor(), note="下游验证通过")
    db_session.commit()
    db_session.expire_all()

    # applied 后：换算成功 = 100g
    r2 = client.post(
        "/api/v1/units/convert",
        json={"value": 1, "from_unit": "盒d", "to_unit": "g",
              "entity_type": "ingredient", "entity_id": ing_id},
    )
    assert r2.status_code == 200
    # value 为 Decimal 序列化为字符串，转 float 比较
    assert abs(float(r2.json()["value"]) - 100.0) < 0.01
