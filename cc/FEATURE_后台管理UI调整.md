# 后台管理 UI 调整：合并翻译配置页 + 移除 USDA 数据页

## 背景

后台管理原有「AI 配置」「机翻配置」两个独立页面，以及一个功能已被「数据维护中心」完全覆盖的「USDA 数据」冗余页。本次：合并两配置页为一、移除冗余页、重排后台导航。

## 改动

### 1. 合并 AI 配置 + 机翻配置 → 单页「AI 与机翻配置」（`/admin/ai-config`）
- `v-expansion-panels multiple` 双面板（AI 翻译 / 机器翻译），默认全展开（`openPanels=[0,1]`）。
- 补标准顶部导航栏 `v-app-bar`（侧边栏切换 + 返回按钮 + 标题），与单位管理、数据维护中心等 admin 子页一致（原 `AiConfigView`/`MtConfigView` 历史遗留漏了这层）；内容区 `<h2>` 改由 app-bar 标题承担。
- 抽 `components/admin/ProviderCard.vue` 子组件，按 `fields` 配置数组 `v-for` 渲染 6 个 provider（`claude_code`/`openai`/`anthropic` + `baidu`/`aliyun`/`deepl`），字段差异完全由声明式配置表达（switch/text/password）。
- 底部一个「保存配置」按钮统一保存（一次 `putTranslationConfig` 存 AI+机翻），消除原两页几乎一字不差的 `setField`/`testProvider`/`save` 重复逻辑（DRY）。
- `/admin/mt-config` 改为重定向到 `/admin/ai-config`（旧书签不失效，与 `recipe-import` 同手法）。

### 2. 移除 USDA 数据页
- 删 `UsdaDataView.vue` + 路由 + 后台导航项。
- 功能已由数据维护中心 100% 覆盖（统计概览、下载 Foundation+SR Legacy、上传 zip、未映射营养素清单、任务状态），无功能丢失。

### 3. 后台导航重排
邀请码 → 单位 → 地图 → **AI 与机翻配置** → **数据维护中心** → Agent 任务台。

## 文件清单

- 新增：`frontend/src/components/admin/ProviderCard.vue`
- 改：`frontend/src/views/admin/AiConfigView.vue`、`frontend/src/router/index.ts`、`frontend/src/views/admin/AdminDashboard.vue`
- 删：`frontend/src/views/admin/MtConfigView.vue`、`frontend/src/views/admin/UsdaDataView.vue`
- 后端：无改动（`getTranslationConfig`/`putTranslationConfig`/`testTranslationConnection` 接口不变）

## 设计/计划文档
- 设计：`docs/superpowers/specs/2026-06-21-后台管理UI调整-design.md`
- 计划：`docs/superpowers/plans/2026-06-21-后台管理UI调整.md`

## 验证
- `npm run build` 全量通过（exit 0）。
- 运行时（需登录态手动确认）：`/admin/mt-config` 重定向到合并页；合并页两组面板默认全展开、6 个 provider 测试/保存可用；`/admin` 导航顺序正确、无「机翻配置」「USDA 数据」入口；数据维护中心 USDA 功能不受影响。
