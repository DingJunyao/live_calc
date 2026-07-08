# 系统文档

## 背景

原系统文档零散且过时：

- 根 `README.md` 功能特性只列 4 条（实际系统早有地图/推荐/多用户/Agent/K线/导出等一大堆）
- `backend/README.md` 严重过时（写 Poetry + `alembic upgrade head` + 错误 API 示例，实际用 uv、建库走 `create_all`）
- `docs/run.md` 用 pip（应为 uv）
- `docs/conf.md` 基本合身但偏开发者
- `cc/DEPLOYMENT.md` 编造 Docker Compose（根目录根本无 `docker-compose.yml`）
- `cc/` 下其余是给开发者和 Claude Code 的工作笔记，非面向最终用户

## 结构（按功能分，不分角色）

```
docs/
├── README.md            总导航（按角色给阅读路径 + 功能/后台分组索引）
├── concepts.md          核心概念与计算逻辑（七节：实体模型/原料关系/价格体系/时间口径/聚合计算/营养/数据归属）
├── getting-started.md   入门（注册/界面/单位偏好/多用户与提议-审核）
├── prices.md            价格记录（记价/快速填写/粘贴导入/趋势/K线/编辑删除）
├── recipes.md           菜谱与成本（浏览/创建编辑/成本计算/半成品传递/发布）
├── ingredients.md       原料与商品（详情页/商品加权/改删审核/拆分/合并/层级）
├── units-density.md     单位与密度（单位系统/实体覆盖/密度/审核）
├── nutrition.md         营养分析（数据来源/USDA匹配/NRV/kcal-kJ）
├── recommend.md         今日推荐（生成机制/换一个/黑名单/本地日缓存）
├── merchants-map.md     商家与地图（商家管理/定位/常用地点/多引擎）
├── profile.md           个人中心（单位偏好/营养目标/常用地点/数据导出/账户安全）
└── admin/               后台管理与运维（管理员专属）
    ├── README.md          后台导航 + 管理员特权
    ├── deploy.md          部署（uv+npm，无 Docker；并掉旧 docs/run.md）
    ├── config-init.md     配置项逐项详解 + 首次启动（并掉旧 docs/conf.md）
    ├── upgrade-backup.md  升级/备份/恢复/日志/排障
    ├── review.md          提议审核台（生命周期/策略/diff/反级联回滚/各执行器）
    ├── agent.md           Agent 任务台（受控只读 MCP + sql_guard + 多轮 loop）
    ├── data-maintenance.md 数据维护中心（导入/USDA/AI后处理/任务列表合并）
    └── users-units-map.md 用户管理/邀请码/单位管理/地图配置
```

## 编法讲究

- **概念文档先行（DRY）**：`concepts.md` 讲清实体关系/价格加权/时间口径/成本计算/营养，功能篇链过去不重复
- **按功能分而非按角色**：用户和管理员在同一功能上操作相似（差别在审核 vs 直写），功能篇内用差异表标注，避免同件事说两遍
- **审核差异统一标注**：每个涉及共享数据的功能篇都有"普通用户审核 / 管理员直写"差异表
- **时间口径写统一版**：因 [[FEATURE_时间口径统一为用户本地日]] 已完成，`concepts.md` D 节只写"用户本地日 + X-Timezone"一种口径，不标注历史不一致
- **无 emoji**（遵 `cc/DEV_RULE.md`）、中文、复用 `docs/img/` 不补图（YAGNI）
- **进阶小节标注**：`concepts.md` 的计算逻辑标"进阶"，普通用户可跳

## 旧文档处置（重构整合）

- 根 `README.md`：精简为门面（标题 + 指向 docs 的四条阅读路径 + 致谢），删过时的功能特性清单
- `backend/README.md`：极简为"指向 docs/admin/deploy + uv 快速启动"，纠正 Poetry/alembic 错误
- `docs/conf.md`、`docs/run.md`：删除，内容并入 `admin/config-init.md` + `admin/deploy.md`
- `cc/` 下文档：不动（给开发者和 Claude Code 的工作笔记，非面向最终用户；本次甄别了其中过时/编造内容——如 DEPLOYMENT 的 Docker——没抄进 admin）
- `docs/plans`、`docs/superpowers`：忽略（用户明确要求）

## 产出

18 篇正文（1 总导航 + 1 核心 + 9 功能 + 8 后台，含 2 个子导航），未 commit。

brainstorming spec 未单独立文件（设计在对话里走完第 1-2 节后被时间口径改造打断）；改造完成后直接执行文档撰写。
