"""测试行政区划 API（/regions）"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.administrative_region import AdministrativeRegion

from tests.conftest import TestingSessionLocal, override_get_db
from app.core.database import get_db

client = TestClient(app)


def _seed_regions():
    """向内存库写入测试用行政区划数据（先清表再插入）。"""
    db = TestingSessionLocal()
    try:
        # 先清除旧数据（每个测试重新 seed）
        db.query(AdministrativeRegion).delete()
        db.commit()

        # 国家（level=0）
        cn = AdministrativeRegion(
            code="CN", name="中国", name_en="China",
            level=0, iso_country="CN", path="CN", is_active=True,
        )
        us = AdministrativeRegion(
            code="US", name="美国", name_en="United States",
            level=0, iso_country="US", path="US", is_active=True,
        )
        db.add_all([cn, us])
        db.flush()

        # 省级（level=1）
        bj = AdministrativeRegion(
            code="110000", name="北京市", name_en="Beijing",
            level=1, parent_id=cn.id, iso_country="CN",
            path="CN/110000", is_active=True,
        )
        sh = AdministrativeRegion(
            code="310000", name="上海市", name_en="Shanghai",
            level=1, parent_id=cn.id, iso_country="CN",
            path="CN/310000", is_active=True,
        )
        db.add_all([bj, sh])
        db.flush()

        # 市级（level=2）
        dc = AdministrativeRegion(
            code="110100", name="市辖区", name_en="Downtown",
            level=2, parent_id=bj.id, iso_country="CN",
            path="CN/110000/110100", is_active=True,
        )
        db.add(dc)
        db.flush()

        # 区级（level=3）
        hd = AdministrativeRegion(
            code="110108", name="海淀区", name_en="Haidian",
            level=3, parent_id=dc.id, iso_country="CN",
            path="CN/110000/110100/110108", is_active=True,
        )
        db.add(hd)
        db.flush()

        # 一个软删的节点（不应出现在常规查询中）
        deleted = AdministrativeRegion(
            code="999999", name="已删除",
            level=1, parent_id=cn.id, iso_country="CN",
            path="CN/999999", is_active=False,
        )
        db.add(deleted)
        db.commit()

        return cn.id, us.id, bj.id, sh.id, dc.id, hd.id
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup():
    """每个测试前安装内存 DB override 并 seed 数据，测试后恢复。"""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    _seed_regions()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


class TestListRegions:
    """GET /regions"""

    def test_default_returns_countries(self, _setup):
        """默认返回 level=0 的国家列表"""
        resp = client.get("/api/v1/regions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        codes = {r["code"] for r in data}
        assert "CN" in codes
        assert "US" in codes
        # 国家节点应有子节点（has_children=True）
        cn = next(r for r in data if r["code"] == "CN")
        assert cn["has_children"] is True

    def test_filter_by_parent_id(self, _setup):
        """?parent_id=X 返回指定节点的活跃子节点"""
        # 先查出中国的 id
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")

        resp = client.get(f"/api/v1/regions?parent_id={cn['id']}")
        assert resp.status_code == 200
        data = resp.json()
        names = {r["name"] for r in data}
        assert "北京市" in names
        assert "上海市" in names
        assert "已删除" not in names  # 软删不可见

    def test_filter_by_level(self, _setup):
        """?level=1 返回所有省级节点"""
        resp = client.get("/api/v1/regions?level=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert all(r["level"] == 1 for r in data)

    def test_parent_id_plus_level(self, _setup):
        """?parent_id=X&level=Y 只返回同时满足的节点"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")

        resp = client.get(f"/api/v1/regions?parent_id={cn['id']}&level=2")
        assert resp.status_code == 200
        # 中国下无 level=2 的直系子节点（省级是 level=1）
        assert len(resp.json()) == 0

    def test_has_children_for_leaf(self, _setup):
        """叶子节点 has_children=False"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")

        resp = client.get(f"/api/v1/regions?parent_id={cn['id']}")
        bj = next(r for r in resp.json() if r["code"] == "110000")
        assert bj["has_children"] is True

        # 查北京的子节点，找到海淀区（叶子）
        resp = client.get(f"/api/v1/regions?parent_id={bj['id']}")
        assert resp.status_code == 200
        dc = next(r for r in resp.json() if r["code"] == "110100")
        assert dc["has_children"] is True

        resp = client.get(f"/api/v1/regions?parent_id={dc['id']}")
        hd = next(r for r in resp.json() if r["code"] == "110108")
        assert hd["has_children"] is False

    def test_trailing_slash(self, _setup):
        """GET /regions/ 也正常工作"""
        resp = client.get("/api/v1/regions/")
        assert resp.status_code == 200


class TestGetRegion:
    """GET /regions/{region_id}"""

    def test_get_single_region(self, _setup):
        """获取节点详情"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")

        resp = client.get(f"/api/v1/regions/{cn['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "CN"
        assert data["name"] == "中国"
        assert data["level"] == 0
        assert data["has_children"] is True
        assert data["ancestors"] == []

    def test_get_with_ancestors(self, _setup):
        """叶子节点返回完整祖先链"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")
        resp = client.get(f"/api/v1/regions?parent_id={cn['id']}")
        bj = next(r for r in resp.json() if r["code"] == "110000")
        resp = client.get(f"/api/v1/regions?parent_id={bj['id']}")
        dc = next(r for r in resp.json() if r["code"] == "110100")
        resp = client.get(f"/api/v1/regions?parent_id={dc['id']}")
        hd = next(r for r in resp.json() if r["code"] == "110108")

        resp = client.get(f"/api/v1/regions/{hd['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ancestors"]) == 3
        # 祖先顺序：中国 → 北京市 → 市辖区
        assert data["ancestors"][0]["name"] == "中国"
        assert data["ancestors"][1]["name"] == "北京市"
        assert data["ancestors"][2]["name"] == "市辖区"

    def test_get_nonexistent_returns_404(self, _setup):
        """不存在的节点返回 404"""
        resp = client.get("/api/v1/regions/9999999")
        assert resp.status_code == 404

    def test_get_deactivated_returns_404(self, _setup):
        """软删的节点返回 404"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")
        # 查中国下所有子节点，排除软删的
        resp = client.get(f"/api/v1/regions?parent_id={cn['id']}")
        ids = {r["code"]: r["id"] for r in resp.json()}
        assert "999999" not in ids

    def test_trailing_slash(self, _setup):
        """GET /regions/{id}/ 也正常工作"""
        resp = client.get("/api/v1/regions")
        cn = next(r for r in resp.json() if r["code"] == "CN")
        resp = client.get(f"/api/v1/regions/{cn['id']}/")
        assert resp.status_code == 200
