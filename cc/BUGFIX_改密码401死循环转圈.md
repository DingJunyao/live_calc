# 改密码输错原密码致 401 死循环转圈

## 现象
个人中心「修改密码」对话框输错原密码，点确定后一直转圈，后台频繁报 `PUT /api/v1/auth/me/account` 401「当前密码错误」（同一时刻多条来自不同 client 端口），刷新页面后密码未更改、也无前端错误提示。

## 根因
[client.ts](frontend/src/api/client.ts) 响应拦截器的 401 处理只对 `/auth/login` 排除 refresh（见 [BUGFIX_登录401刷新冲掉错误](BUGFIX_登录401刷新冲掉错误.md)），其它 401 一律走 refresh+重放分支。`/auth/me/account` 的「当前密码错误」是**业务校验型 401**——refresh 救不了（token 本身没坏，是密码不对），重放照样 401；而拦截器无「已重试」刹车位，于是无限 `refresh（成功）→ 重放 → 401 → refresh → 重放 → 401 …` 死循环。`return api.request(error.config)` 永不 reject，[ProfileView saveChangePassword](frontend/src/views/profile/ProfileView.vue#L764) 的 `catch` 收不到错误，`savingPassword` 永真 → 转圈、`notify` 不触发。日志里「两条不同端口的同请求」就是「原始 + refresh 后重放」一轮的快照，实际持续在刷。

后端三处密码端点同构（前端 SHA256 + 后端 bcrypt 双层，详见 [auth.py:155/190/412](backend/app/api/auth.py)）：login / register / update_my_account 都把前端入参当 SHA256 哈希处理。`/auth/me/account` 的 401 纯粹是「业务校验型」（当前密码不对），与 token 过期同返 401、后端无法区分，必须由前端拦截器处理。

## 修复
[client.ts](frontend/src/api/client.ts) 加 `_retry` 单次重试标志位（axios 社区标准范式）：

- 条件改 `if (!isLoginRequest && !(error.config as any)?._retry)`
- 重放前 `(error.config as any)._retry = true`

效果：首次 401 → refresh → 标记 → 重放（仅此一次）；重放若再 401 且已标记 → 跳过 refresh，透传给 `extractErrorDetail` + `reject`，UI 显示「修改失败：当前密码错误」。

四场景走查：
- token 过期、密码对：首次 401 → refresh → 重放 → 200 ✓
- 密码错：首次 401 → refresh（成功）→ 重放 → 401 → `_retry` 跳过 → 显示「当前密码错误」✓
- login 凭证错：`isLoginRequest` 跳过，不受影响 ✓
- token 过期叠加密码错：refresh 一次后重放仍 401 → 跳过 → 显示「当前密码错误」✓

## 技术点
- `_retry` 挂在 `error.config` 上，随重放（同一个 config 引用）传递到二次 401。
- TS strict 模式下自定义字段用 `as any` 断言（项目 `build` 是 `vite build` 不跑 vue-tsc，但 IDE 会报红，断言处理干净）。
- 「业务校验型 401」与「token 过期 401」后端都返 401 无法区分；用「重试一次」边界区分——refresh 能解决的 token 过期一次就过，解决不了的业务 401 重试仍 401 落 reject。一举杜绝所有「已登录用户业务校验型 401」端点的死循环（不只改密码，未来同类端点自动受益）。

## 改动范围
纯前端单文件 [client.ts](frontend/src/api/client.ts)，无表结构变更，`npm run build` 通过（13.69s，PWA precache 114 条）。

## 教训
「登录 401」那关只堵了 `/auth/login` 一个端点，没抽象出「业务校验型 401 一律不该触发 refresh」的通则——凡是已登录用户主动发起、可能因业务原因返 401 的端点（改密码、改邮箱需重新验证等）都会踩同款死循环。单次重试标志位是这类问题的根治范式，比逐个端点加白名单更省心。
