# USDA 营养素匹配

## 功能

原料/商品手动匹配 USDA 营养素：下载 USDA 原始数据（Foundation + SR Legacy）入库、翻译食材名称（6 后端）、前端搜索匹配并写入营养数据。与现有 `nutrition_import_service`（HowToCook 精简版批量导入）并存、互不干扰。

## 架构

- **数据层**：`usda_foods` / `usda_food_nutrients` / `translation_configs` / `usda_tasks` 四表；解析去重（同 description 留最优一条，foundation 优先）；upsert 入库；内存 OR 子串搜索（空格分词、任意命中、精确>前缀>包含打分）。
- **翻译层**：`Translator` 抽象 + 6 后端（Claude Code CLI / OpenAI 兼容 / Anthropic 兼容 / 百度 / 阿里云 / DeepL）；营养素名走 172 条预设映射表（对齐 live_calc「能量」体系，不耗 AI）；增量翻译（`translate_status` pending/done/error）+ 进度写 `usda_tasks` + 单批重试 3 次；每后端 `health_check` 测试连接。
- **匹配交互**：原料清空写 USDA；商品清空 → 复制所属原料营养素骨架设 0 → USDA 覆盖（`custom_nutrition_data` 三层结构对齐前端读取）；`source=usda_manual_match`，记录 `usda_id`。
- **后台三页**：AI 配置 / 机翻配置 / USDA 数据（统计/下载/上传/翻译 6 选 1/任务轮询/未映射清单）。

## 关键端点

- 用户：`GET /api/v1/usda/search`、`GET /api/v1/usda/{fdc_id}`、`POST /api/v1/usda/match/ingredient/{id}`、`POST /api/v1/usda/match/product/{id}`
- 后台（admin）：`GET/PUT /api/v1/admin/translation-config`、`POST .../translation-config/test`、`POST /api/v1/admin/usda/{download,upload,translate}`、`GET .../usda/{task,statistics,unmapped-nutrients}`

## 设计决策

数据源 Foundation + SR Legacy；全量预翻译；营养素名预设映射表；数据库存储 + 内存索引搜索；同 description 去重留最优；Anthropic 带 base_url（兼容端点）；翻译/AI HTTP 超时 3600s（`translate_http_timeout`）；后台 AI/机翻/USDA 三页独立。

## 待办 / 注意

- **权限**：匹配端点现为「登录即可」（与项目现有写端点一致），TODO 复用 owner/admin 校验（现有写端点亦无此校验）。
- **`fetch_dataset_urls`**（USDA 下载页抓取直链）留 `NotImplementedError`，需对照 `D:\code\HowToCook_json_organizer\scripts\build_usda_data.py` 补全 HTML 解析。
- **商品 `all_nutrients` 英文 key 渲染**：与现有 `NutritionData` 存储格式一致（英文 key），前端「其他营养素」展示分支待配真实数据后手动验证（Task 21 reviewer 提示）。
- **全量 pytest 有 13 个既有失败**（真实库残留用户 + 路由漂移，如 `POST /recipes/` 405），与本功能无关；本功能相关测试（USDA + services + models）全绿。建议另起任务治理既有失败。
- **翻译/测试连接成功路径**涉及真实网络，需配真实密钥后手动验证（单测只覆盖 mock + 400 路径）。

## 文档

- 设计：`docs/superpowers/specs/2026-06-16-USDA营养素匹配-design.md`
- 计划：`docs/superpowers/plans/2026-06-16-USDA营养素匹配.md`
