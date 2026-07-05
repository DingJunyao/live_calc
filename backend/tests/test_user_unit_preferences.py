"""用户单位偏好 /auth/me 测试。

跟随 test_auth.py 模式：模块级 TestClient + 真实开发库，直接 register 写入。
每个测试用唯一 username 隔离，避免跨测试状态污染。
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _register_and_login(username: str) -> str:
    """注册指定用户（重名幂等）并登录，返回 access_token。"""
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@test.com",
            "password_hash": "pw_hash",
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password_hash": "pw_hash"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _get_unit_ids(token: str):
    """从 /units/ 取 mass/volume/count 各一个 id。返回 (mass, volume, count)。"""
    resp = client.get(
        "/api/v1/units/",
        params={"limit": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", [])
    mass = next((u["id"] for u in items if u.get("unit_type") == "mass"), None)
    volume = next((u["id"] for u in items if u.get("unit_type") == "volume"), None)
    count = next((u["id"] for u in items if u.get("unit_type") == "count"), None)
    return mass, volume, count


def test_get_me_returns_unit_preferences_null_when_unset():
    token = _register_and_login("unitpref_get")
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    up = resp.json()["unit_preferences"]
    assert up["energy_unit"] is None
    assert up["mass_unit"] is None
    assert up["volume_unit"] is None
    assert up["price_unit"] is None


def test_patch_me_sets_unit_preferences():
    token = _register_and_login("unitpref_set")
    mass_id, volume_id, count_id = _get_unit_ids(token)
    assert mass_id, "缺少 mass 类型单位"
    assert volume_id, "缺少 volume 类型单位"
    assert count_id, "缺少 count 类型单位"

    resp = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "default_energy_unit": "kJ",
            "default_mass_unit_id": mass_id,
            "default_volume_unit_id": volume_id,
            "default_price_unit_id": count_id,
        },
    )
    assert resp.status_code == 200, resp.text
    up = resp.json()["unit_preferences"]
    assert up["energy_unit"] == "kJ"
    assert up["mass_unit"]["id"] == mass_id
    assert up["volume_unit"]["id"] == volume_id
    assert up["price_unit"]["id"] == count_id


def test_patch_me_rejects_wrong_unit_type():
    """把 volume 单位塞给 mass 字段应 400。"""
    token = _register_and_login("unitpref_wrong")
    _, volume_id, _ = _get_unit_ids(token)
    assert volume_id, "缺少 volume 类型单位"

    resp = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_mass_unit_id": volume_id},
    )
    assert resp.status_code == 400, resp.text


def test_patch_me_rejects_invalid_energy_unit():
    token = _register_and_login("unitpref_energy")
    resp = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_energy_unit": "calorie"},
    )
    assert resp.status_code == 400, resp.text


def test_patch_me_clears_preference_with_null():
    token = _register_and_login("unitpref_clear")
    mass_id, _, _ = _get_unit_ids(token)
    assert mass_id, "缺少 mass 类型单位"

    # 先设
    r1 = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_mass_unit_id": mass_id},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["unit_preferences"]["mass_unit"] is not None

    # 再清
    resp = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"default_mass_unit_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["unit_preferences"]["mass_unit"] is None
