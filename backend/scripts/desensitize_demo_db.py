"""把开发库脱敏成演示版本。

精简到两个用户：admin(id=1) / test(id=12)，密码统一 123456，邮箱归
admin@example.com / test@example.com。其余用户硬删（业务表零引用，删无孤儿）。
顺手清理 id=2（早已删除用户）在审计字段留下的 3 条残留，归到 admin(1)。

用法（在 backend/ 目录下）::

    ../.venv/Scripts/python.exe scripts/desensitize_demo_db.py [db_path]

默认目标 data/livecalc.db。执行前自动带时间戳备份。脚本幂等：重复跑只会
再次确认两个保留账号、再清一次残留，已删用户再删为空操作。

注意：密码哈希用项目同一套 bcrypt(rounds=12)，与 app/core/security.py 对齐，
保证改完用 123456 能正常登录。本脚本只动 users 表与 3 条审计残留，业务数据
（菜谱/价格/商品/原料…）原样保留作为演示内容。
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import bcrypt

DEMO_PASSWORD = "123456"
KEEP_IDS = (1, 12)  # admin / test
KEEP_USERNAMES = {1: "admin", 12: "test"}
KEEP_EMAILS = {1: "admin@example.com", 12: "test@example.com"}


def _sha256_hex(password: str) -> str:
    """对齐前端 crypto-js ``SHA256().toString()`` 的小写 hex 输出。

    前端 ``utils/crypto.ts`` 在登录/注册/改密前先做一次 SHA256 再发给后端，
    故库里实际存的是 ``bcrypt(SHA256_hex(明文))``，而非 ``bcrypt(明文)``。
    若脱敏时直接存 ``bcrypt("123456")``，前端登录传 ``SHA256("123456")``
    会比对失败，演示库密码登不上。
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def password_hash() -> str:
    """生成 ``bcrypt(SHA256(明文))``（rounds=12，与 security.py 对齐）。"""
    sha = _sha256_hex(DEMO_PASSWORD)
    return bcrypt.hashpw(sha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def main(db_path: str) -> int:
    db = Path(db_path)
    if not db.exists():
        print(f"[ERR] 数据库不存在: {db}")
        return 1

    # 1) 备份
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = db.with_name(f"{db.name}.bak_desensitize_{ts}")
    shutil.copy2(db, bak)
    print(f"[备份] {db} -> {bak}")

    pwd = password_hash()
    # 自检：库里存 bcrypt(SHA256(明文))，校验时同样先 SHA256
    assert bcrypt.checkpw(_sha256_hex(DEMO_PASSWORD).encode(), pwd.encode()), "bcrypt 自检失败"

    con = sqlite3.connect(str(db), timeout=30)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    before = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f"[改前] users 共 {before} 条")

    # 2) 原子事务执行全部变更
    with con:  # 自动 commit / 异常回滚
        # 2a) 统一密码 + token_version 归零（演示库干净起点）
        n_pwd = cur.execute(
            "UPDATE users SET password_hash = ?, token_version = 0",
            (pwd,),
        ).rowcount
        # 2b) 两个保留账号的 username / email 显式确认（不依赖现状）
        for uid in KEEP_IDS:
            cur.execute(
                "UPDATE users SET username = ?, email = ? WHERE id = ?",
                (KEEP_USERNAMES[uid], KEEP_EMAILS[uid], uid),
            )
        # 2c) 硬删其余用户（业务表零引用，无孤儿）
        placeholders = ",".join("?" * len(KEEP_IDS))
        n_del = cur.execute(
            f"DELETE FROM users WHERE id NOT IN ({placeholders})", KEEP_IDS
        ).rowcount
        # 2d) 清理 id=2（已删用户）审计残留 -> admin(1)
        n_ing = cur.execute(
            "UPDATE ingredients SET created_by = 1 WHERE created_by = 2"
        ).rowcount
        n_prod_c = cur.execute(
            "UPDATE products SET created_by = 1 WHERE created_by = 2"
        ).rowcount
        n_prod_u = cur.execute(
            "UPDATE products SET updated_by = 1 WHERE updated_by = 2"
        ).rowcount

    print(
        f"[变更] 改密码 {n_pwd} 条 / 硬删用户 {n_del} 条 / "
        f"清 id=2 残留: ingredients.created_by {n_ing} + "
        f"products.created_by {n_prod_c} + products.updated_by {n_prod_u}"
    )

    # 3) 验证
    print("\n[验证] users 最终状态:")
    for r in cur.execute(
        "SELECT id, username, email, is_admin, is_active, token_version, "
        "length(password_hash) AS plen FROM users ORDER BY id"
    ).fetchall():
        d = dict(r)
        ok = bcrypt.checkpw(_sha256_hex(DEMO_PASSWORD).encode(), _pwd(con, d["id"]))
        print(
            f"  id={d['id']} {d['username']}/{d['email']} "
            f"is_admin={d['is_admin']} token_ver={d['token_version']} "
            f"hash_len={d['plen']} verify(sha256·123456)={ok}"
        )

    # 引用完整性复查：真用户引用列不得指向已删用户
    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic%'"
        ).fetchall()
    ]
    ref_cols = []
    for t in tables:
        for fk in cur.execute(f"PRAGMA foreign_key_list({t})").fetchall():
            if fk[2] == "users":
                ref_cols.append((t, fk[3]))
    dangling = 0
    for t, c in ref_cols:
        n = cur.execute(
            f"SELECT COUNT(*) FROM {t} WHERE {c} IS NOT NULL AND {c} NOT IN (?, ?)",
            KEEP_IDS,
        ).fetchone()[0]
        if n:
            dangling += n
            print(f"  [警告] {t}.{c} 仍有 {n} 条指向已删用户")
    print(f"[引用完整性] 残留指向已删用户的引用: {dangling} 条（应为 0）")

    after = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f"[改后] users 共 {after} 条")

    # 4) VACUUM 收缩（非必须，失败不中断）
    con.commit()
    try:
        cur.execute("VACUUM")
        print("[VACUUM] 完成")
    except sqlite3.OperationalError as e:
        print(f"[VACUUM] 跳过（{e}）")

    con.close()
    print(f"\n[完成] 备份保留于 {bak}")
    print(f"       演示库 {db} 已就绪：admin/{DEMO_PASSWORD} 与 test/{DEMO_PASSWORD}")
    return 0


def _pwd(con: sqlite3.Connection, uid: int) -> bytes:
    row = con.execute("SELECT password_hash FROM users WHERE id = ?", (uid,)).fetchone()
    return row[0].encode("utf-8")


if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else "data/livecalc.db"
    sys.exit(main(db_arg))
