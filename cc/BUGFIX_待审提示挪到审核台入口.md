# 待审提示从个人中心挪至后台首页「提议审核台」入口

## 现象（用户反馈）

其他（普通）用户提交变更提议后，管理员账号在「个人中心」→「我的提议」菜单项旁看到一个「N 条待审」chip。用户认为该提示属审核台职责，不应出现在个人中心，要求挪到「后台管理」的「提议审核台」。

## 根因（双重）

1. **位置错放**：该 badge 原挂在 [ProfileView.vue](../frontend/src/views/profile/ProfileView.vue) 个人中心「我的提议」v-list-item 的 append，但「待审提示」语义上属管理员审核职责，应在审核台入口而非个人中心。
2. **scope 漏传（放大误显）**：原 [ProfileView loadPendingCount](../frontend/src/views/profile/ProfileView.vue) 调 `listProposals('pending', 1)` 漏传 `scope='mine'`，后端 [list_proposals:206](../backend/app/api/proposals.py#L206) 「不传 scope + 管理员」走全表语义，故他人提交的 pending 也会点亮管理员的个人中心 badge（属 commit `72fdead`「我的提议混入他人提议」同源漏网——那次修了列表 [MyProposalsView:226](../frontend/src/views/profile/MyProposalsView.vue#L226) / [proposals.ts](../frontend/src/api/proposals.ts) / 后端三处对齐 `mine`，漏了 ProfileView 这个计数）。附带 `limit=1` 致数量永远 ≤1。

## 方案（用户拍板：换地方，非修 scope）

用户明确要求「换个地方」——个人中心删、审核台加。故**不采用**「补 `scope=mine` 让管理员只看自己 pending」的保守修法（姐姐第一轮曾误采此法，后据用户澄清纠正）。

### 删：ProfileView 个人中心 badge

[ProfileView.vue](../frontend/src/views/profile/ProfileView.vue) 四处：
- 模板：「我的提议」list-item append 的 `<v-chip>` 删除（保留 chevron 图标）
- script：删 `pendingProposalCount` ref、`loadPendingCount` 函数、`onMounted` 里的 `loadPendingCount()` 调用
- import：删 `listProposals`（grep 确认仅此处使用，删后无残留）

### 加：AdminDashboard 审核台入口 badge

[AdminDashboard.vue:81](../frontend/src/views/admin/AdminDashboard.vue#L81) 「提议审核台」v-list-item 的 append 加：

```html
<v-chip v-if="pendingProposalCount > 0" color="warning" size="small" class="me-1">
  {{ pendingProposalCount }} 条待审
</v-chip>
```

放在 chevron 图标前。与原个人中心 badge 形态/位置完全对称（同为 v-list-item append 内的 warning chip）。script 加 `pendingProposalCount` ref + `loadPendingCount`（调 `listProposals('pending', 100)` **不传 scope** 取全表待审数）+ `onMounted` 调用。

**关键**：审核台入口用全表计数（不传 scope），这是管理员审核视角——要看所有用户提交的待审，与原 ProfileView bug 的语义正好相反（那边是「不该看全表却看了」，这边是「就该看全表」）。

### 审核台页内不动

[ProposalsView](../frontend/src/views/admin/ProposalsView.vue) 默认筛选即「待审」（[:666](../frontend/src/views/admin/ProposalsView.vue#L666)）、列表上方已显示「共 N 条」，页面内不重复加提示。用户拍板提示只放后台首页入口（不放审核台页内，也不两处都放）。

## 为何用全表计数（不传 scope=mine）

审核台是管理员审核**所有用户**提议的工作台，待审数 = 全表 pending 总数。若传 `scope=mine` 只数管理员自己提交的，badge 会恒空（管理员日常走 `apply_as_admin` 直写、status=applied 不产生 pending），失去提示意义。

## 验证

- 纯前端双文件改动（[AdminDashboard.vue](../frontend/src/views/admin/AdminDashboard.vue) + [ProfileView.vue](../frontend/src/views/profile/ProfileView.vue)），`npm run build` 通过（25.35s，仅有与本次无关的 chunk 体积既有警告）。
- 无后端改动、无表结构变更（无 alembic / SQL 脚本）。
- 手动验证（待跑）：普通用户提交一条提议 → 管理员登录后台首页 →「提议审核台」入口显示「N 条待审」chip；个人中心「我的提议」项干净无 chip。

## 教训

姐姐第一轮把用户「换个地方」理解成「修对语义保留原位」，方向搞反。用户澄清后纠正——遇到「应该在 A 不在 B」类反馈，先确认是「修 B 的数据」还是「把 B 挪到 A」，别默认前者。
