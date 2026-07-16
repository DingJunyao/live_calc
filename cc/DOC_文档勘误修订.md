# 文档勘误修订（docs/ 正文）

逐一对照代码审查后修订 docs/ 正文（不含 plans/superpowers 草稿）。问题清单在对话中逐条带代码依据确认。

## 修订项

- [deploy.md](../docs/admin/deploy.md)：第 3 行「没有 Docker 部署」改口为「支持 Docker（推荐）+ 手动两种」；新增「## Docker 部署」章（Dockerfile multi-stage 三 target、`docker-compose.yml`/`docker-compose.split.yml`、`deploy/`、`docker compose up -d --build`、换库改 DATABASE_URL、Docker 未封装 Claude Code）。根因：容器化早已做（FEATURE_容器化部署），文档却写「没有」。
- [config-init.md](../docs/admin/config-init.md)：删伪环境变量 `REGISTRATION_REQUIRE_INVITE_CODE`（实际在 `system_config` 表、由后台「邀请码管理」页面开关控制，非 .env，见 [auth.py](../backend/app/api/auth.py) `_get_bool_config`）；`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` 15→10080（与 [config.py](../backend/app/config.py) 默认 7 天一致）；修坏链。
- [review.md](../docs/admin/review.md)「覆盖的改动类型」：按 [bootstrap.py](../backend/app/services/proposals/bootstrap.py) 补全（原料含合并/商品含合并拆分/商品营养/USDA 原料+商品匹配/商家含合并/菜谱发布+已发布菜谱编辑），「菜谱图片删除」举例改为「菜谱发布 + 已发布菜谱编辑」（无独立图片删除执行器）。
- [recommend.md](../docs/recommend.md)：「黑名单 / 过敏原」空小节补正文（黑名单排除候选菜谱、过敏原分组管理员维护）。
- [admin-pages.md](../docs/admin/admin-pages.md)：地图配置补「启用的地图服务 / 地理编码服务」开关（[MapSettingsView.vue](../frontend/src/views/admin/MapSettingsView.vue) 确有）；开头补后台首页 Dashboard 统计卡描述。
- [ingredients.md](../docs/ingredients.md)：第 80 行 `[商品合并](...)` 补 `!`（图片笔误，渲染成链接）。
- 幽灵文件坏链 `users-units-map.md`（不存在，实为 admin-pages.md）3 处全修：[profile.md](../docs/profile.md)、[merchants-map.md](../docs/merchants-map.md)、[config-init.md](../docs/admin/config-init.md)。
- [docs/README.md](../docs/README.md) + [admin/README.md](../docs/admin/README.md)：后台索引表补漏列的 review/data-maintenance/agent 三篇；deploy 行加 Docker；admin/README「创建菜谱默认发布」过时特权改为「默认私有需手动发布」（FEATURE_菜谱发布默认私有）。

## 审查确认无误（未动）

prices/concepts/getting-started/units-density/nutrition/agent/data-maintenance/upgrade-backup 主体准确。merchants-map「收藏共享商家」（`UserMerchantFavorite` 真存在，旧 `FavoriteMerchant` 表已清但功能用新表重实现，记忆过时）、「换一个默认 5 次」（[meal_recommender.py](../backend/app/services/meal_recommender.py) `MAX_REFRESH_PER_MEAL = 5`）均核实正确。

## K 线

正文 docs 未检出 K 线描述（仅 plans/superpowers 草稿有）；前端代码 5 文件有 K 线残骸但未接路由，对文档无影响，清不清另议。

## 配套

用户信息编辑功能的 profile.md 章节 + 账户安全节改写见 [[FEATURE_用户信息编辑]]。
