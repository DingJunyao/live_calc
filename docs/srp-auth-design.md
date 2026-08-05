# 登录协议改造设计：SRP（Secure Remote Password）

> 状态：**设计草案，待评审，尚未实现**
> 目标：消除客户端 SHA256 预哈希的"可重放凭据"问题（Codex Security C-013）。
> 原则：改动较大，须独立分支、独立 PR、配完整测试（含存量用户迁移回归），不与当前安全修复混在一起。

---

## 1. 背景与问题

### 1.1 现状

登录链路（`backend/app/api/auth.py` `login`、`backend/app/core/security.py`）：

```
前端  utils/crypto.ts: hashPassword = SHA256(password)   // 无盐、确定性
      POST /auth/login { username, password_hash }
后端  verify_password( plain = password_hash, stored = bcrypt(SHA256(pw)) )
```

注册 / 改密 / 管理员建号重置密钥，均以同样的 `password_hash`（SHA256）形态流转。

### 1.2 问题本质

不在于"传输是否加密"（HTTPS 能解决传输窃听），而在于：

- `SHA256(password)` 是**确定性、可重放的凭据等价物**——每次登录都一样，不随会话变化。
- 任何能拿到该值的人（日志、MITM、XSS、反向代理、后端内存 dump、错误回显……），**无需破解 bcrypt、无需知道原密码**，即可原样重放登录。
- 一旦泄露一次，**永久有效**（直到改密码）。

### 1.3 改造目标（传输无关保护）

让密码**永远不以可重放形态出现在网络、日志、内存中**——即便传输通道被剥光（明文 HTTP）、即便服务端把请求体原样落盘，攻击者拿到的也只是**无法直接用于登录的东西**。

---

## 2. 选型：SRP-6a

### 2.1 为什么是 PAKE，而不是"HTTPS + 明文密码"

HTTPS 只解决"传输保密"，但密码仍以明文（或可重放哈希）**到达服务端**。一旦 TLS 在反向代理终止、或代理/网关记录请求体、或服务端有日志/内存泄露，密码就裸奔。PAKE 让密码**根本不离开客户端**，把信任边界从"整条传输链路 + 服务端"收窄到"客户端单点"。

### 2.2 为什么选 SRP-6a

- **成熟**：Web 领域广泛使用，文档与实现多。
- **双向**：SRP-6a 是对称 PAKE，服务端只存验证因子 `v`（单向），客户端持有 `x = H(salt || password)`，双方多轮交换得到共享会话密钥 `K`，但 `x`/密码均不上网。
- **抗离线字典**：中间人无法从交换中离线爆破口令（除非已拿到服务端 `v`）。
- **库生态**：Python（`srptools` 等）、JS/TS（`secure-remote-password` 等）均有现成实现。

备选 **OPAQUE（RFC 9380）** 更现代（抗预计算更强、非对称 PAKE），但 TS 侧成熟库相对少，**留作后续评估**；本期先以 SRP-6a 落地。

---

## 3. SRP-6a 协议回顾（本项目落地版）

参数：大素数 `N`、生成元 `g`、哈希函数 `H`（均由库提供标准参数集）。每个用户有：

- `salt`：随机盐（注册时生成，恒定）
- `x = H(salt, H(username : password))`：客户端口令私钥，**永不上网**
- `v = g^x mod N`：服务端验证因子（verifier），**只存这个**

### 3.1 注册

1. 客户端生成 `salt`，算 `x = H(salt, H(username:password))`，再算 `v = g^x mod N`。
2. 客户端提交 `{ username, salt, v }`（**不传 password、不传 x**）。
3. 服务端存储 `salt` 与 `v`。

### 3.2 登录（两步握手）

**第 1 步：发起挑战**

```
POST /auth/srp/init { username }
```
- 服务端查 `salt`、`v`；生成随机 `b`，算 `B = (kv + g^b) mod N`。
- 返回 `{ salt, B }`，并在服务端会话（内存/Redis，短 TTL）暂存 `b`、`B`（键 = 随机 `challenge_id`，关联 `username`）。

**第 2 步：客户端证明**

客户端（已知 password、收到 `salt`/`B`）：
- 算 `x = H(salt, H(username:password))`、`a`（随机）、`A = g^a mod N`。
- 算会话密钥 `K`、客户端证明 `M1 = H(A, B, K)`。

```
POST /auth/srp/verify { challenge_id, A, M1 }
```

**第 3 步：服务端校验 + 派发令牌**

- 服务端用 `A`、`b`、`v` 重算 `K` 与 `M1`，比对客户端 `M1`。
- 通过后算 `M2 = H(A, M1, K)` 一并返回（客户端可校验服务端，防 MITM）。
- **通过后再签发现有 JWT**（`access_token` / `refresh_token`，含 `sub` + `ver=token_version`），与现有会话体系无缝衔接。

### 3.3 安全要点

- 每次登录 `A`/`B`/`a`/`b` 均为随机，`M1` 一次性 → **不可重放**。
- 密码与 `x` 从不出现在网络、日志、服务端内存（服务端只持 `v`、`b`）。
- `challenge_id` 用后即弃，TTL 短（如 60s），防重放与挂起。

---

## 4. 落地改动点

### 4.1 数据模型（`backend/app/models/user.py`）

新增/调整列：
```
srp_salt      String(64)   nullable   # SRP 盐
srp_verifier  String(700)  nullable   # v = g^x mod N（十六进制/base64）
auth_scheme   String(16)   default 'legacy'   # 'legacy' | 'srp'，区分迁移
```
保留 `password_hash` 列**迁移期不删**（供 `legacy` 用户旧校验）。

### 4.2 后端接口（`backend/app/api/auth.py`）

- 新增 `POST /auth/srp/init`、`POST /auth/srp/verify`。
- `/login`（旧 SHA256 链路）**迁移期保留**，用于 `auth_scheme='legacy'` 用户；迁移完成后移除。
- `/register` 改为接收 `{ username, email, phone, salt, v, invite_code }`。
- `PUT /me/account`（改密）、管理员建号/重置密码：改为接收 `salt`/`v`。
- 新增"**登录时升级**"：`legacy` 用户用旧链路校验通过后，若客户端本轮也带了 `x` 可算出的 `v`（即客户端有明文密码），则写入 `srp_salt`/`srp_verifier`、置 `auth_scheme='srp'`，并 `token_version += 1` 使旧 token 失效。

### 4.3 前端（`frontend/src/utils/crypto.ts` 等）

- `crypto.ts`：从 `SHA256(password)` 改为 SRP 客户端步骤（`x`、`A`、`K`、`M1`、`v` 生成）。
- `Login.vue` / `Register.vue` / `ProfileView.vue` / `admin/UserManagementView.vue`：全部调用点改为 SRP 两步流程。
- 选型建议库：`secure-remote-password`（需核对维护状态与审计）。

### 4.4 安全/日志

- 已有 `_redact_sensitive_body`（本轮 C-006 修复）天然适配：`v`/`M1`/`A`/`B` 虽不可重放，仍建议加入脱敏名单避免噪音。

---

## 5. 存量用户迁移

**关键约束**：现网 `password_hash = bcrypt(SHA256(pw))` 是单向的，**无法反推** `v`。迁移策略：

1. 新注册/改密一律走 SRP，`auth_scheme='srp'`。
2. 存量用户首次用旧链路登录成功后，若客户端本轮持有明文密码（登录场景必然有），则**当场算 `v` 并提交**，服务端写入 `srp_salt`/`srp_verifier`，切换 `auth_scheme='srp'`，`token_version += 1`。
3. 迁移期服务端按 `auth_scheme` 分流校验（legacy 用 bcrypt(SHA256)，srp 用 SRP）。
4. 迁移完成（监控 `auth_scheme='legacy'` 数量趋零）后，移除旧 `/login` 与 `password_hash` 列（单独 PR + alembic 迁移）。

alembic 迁移需新增三列、设默认值；不删 `password_hash` 直到 legacy 用户清零。

---

## 6. 风险与验收

- **协议正确性**：SRP 必须用库实现，**严禁手写**；落地前对握手做单元测试（正常/重放/篡改/M1 不匹配/MITM）。
- **迁移回归**：legacy → srp 升级路径必须有测试，避免误判把用户锁死。
- **会话衔接**：SRP 通过后签发的 JWT 必须与现有 `token_version`、refresh、admin 校验一致。
- **失败与超时**：`challenge_id` TTL、并发发起、网络中断重试要有定义。
- **依赖冲突**：与任何同期改鉴权/用户模型/前端登录的分支冲突，须协调合并顺序。

---

## 7. 建议的推进顺序

1. 本设计文档评审通过。
2. 独立分支 `feat/srp-auth`：后端两步接口 + 数据模型 + 迁移逻辑 + 测试。
3. 前端 SRP 客户端 + 各登录/注册/改密入口。
4. 灰度：新注册走 SRP；存量登录时升级。
5. legacy 清零后移除旧链路与 `password_hash` 列。
