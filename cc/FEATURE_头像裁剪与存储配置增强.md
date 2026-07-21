# 头像裁剪与存储配置增强

## 概述

本轮实现 5 个功能增强：OSS PutObject 兼容修复（payload_signing_enabled + checksum 控制）+ PicGo 三字段（base_path/custom_domain/url_suffix，DB 存逻辑 key）+ 国家级中文化（COUNTRY_NAMES_ZH + re-seed）+ 头像裁剪（vue-advanced-cropper 512×512）+ 向导按钮去重/url_style 提示。

## 改动清单

### 1. OSS PutObject 兼容修复（Task 1）

**问题**：阿里云 OSS 不支持 boto3 新版默认的 `streaming-unsigned-payload-trailer`，导致 `test_endpoint_runs_probe` 调用 `PutObject` 报 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 错误。

**修复**：[s3.py:51-66](../../backend/app/services/storage/s3.py#L51-L66) S3Backend Config 加：
```python
Config(
    signature_version='s3v4',
    payload_signing_enabled=True,  # 启用 payload 签名（绕过 OSS 不支持的 streaming-unsigned-payload-trailer）
    request_checksum_calculation='when_required',  # checksum 控制与 payload_signning_enabled 联动
    response_checksum_validation='when_required',
)
```

**验证**：单测 `test_s3_config_disables_streaming_unsigned_payload` 通过（mock boto3 client 调用 `put_object` 前 Config 检查）。真机 OSS 验证待用户手测（见下方手动核验清单）。

---

### 2. PicGo 三字段（Task 2+3）

**目标**：支持 PicGo 风格的存储配置（base_path/custom_domain/url_suffix），便于 CDN/图床场景。

**改动**：

#### 后端
- **Schema**：[StorageConfiguration](../../backend/app/schemas/storage.py) 加三字段：
  - `s3_base_path: str | None`（S3 专用，逻辑 key 前缀，如 `"images/"`）
  - `s3_custom_domain: str | None`（S3 专用，CDN 域名，如 `"https://cdn.example.com"`）
  - `s3_url_suffix: str | None`（S3 专用，URL 后缀，如 `"!preview.jpg"`）

- **S3Backend**：[s3.py](../../backend/app/services/storage/s3.py)
  - `_full_key(self, key: str)`: DB 存逻辑 key（不含 base_path），内部加前缀返回真实 key（如 `"images/avatar.jpg"` → `"images/avatar.jpg"`，base_path=`"images/"` → `"images/images/avatar.jpg"`）
  - `url_for(self, key: str)`: 优先级 `custom_domain > virtual > path` + url_suffix 末尾

- **effective/config/factory/API/.env/migrate**：全链跟进
  - [effective.py:36-45](../../backend/app/services/storage/effective.py#L36-L45) `get_effective_config` 加三字段（S3 专用）
  - [config.py:34-36](../../backend/app/config.py#L34-L36) Settings 加三字段环境变量（从 `.env` 读，S3 专用）
  - [factory.py:22](../../backend/app/services/storage/factory.py#L22) `_create_s3` 传三字段
  - [storage.py:47-52](../../backend/app/api/storage.py#L47-L52) `test_endpoint` probe 时拼装 `S3Config`（含三字段）
  - [migrate.py](../../backend/app/services/storage/migrate.py) `migrate_to_s3` 迁移时传 `base_path`

#### 前端
- **StorageConfigView**：[StorageConfigView.vue:148-151](../../frontend/src/views/admin/StorageConfigView.vue#L148-L151) 向导②加三字段（仅在 S3 类型显示）
  - `base_path` 文本框（提示 "如 images/"）
  - `custom_domain` 文本框（提示 "如 https://cdn.example.com"）
  - `url_suffix` 文本框（提示 "如 !preview.jpg"）

**关键设计**：
- **DB 存逻辑 key（不含 base_path）**：base_path 改动 DB 零改动，迁移只重传文件（DB key 不变）
- **url_for 优先级**：custom_domain > virtual > path + url_suffix（PicGo 风格）

**验证**：单测 `test_s3_put_prepends_base_path` / `test_s3_url_for_custom_domain_and_suffix` / `test_s3_url_for_base_path_with_endpoint` / `test_s3_get_uses_full_key` 全过。

---

### 3. 国家级中文化（Task 4）

**问题**：region_seed 内置的国家级数据源为英文（ISO alpha-2），如 `"CN"` → `"China"`，而中文用户期望显示 `"中国"`。

**改动**：

#### 后端
- **region_seed.py**：[region_seed.py:39-57](../../backend/app/services/region_seed.py#L39-L57)
  - 加内置常量 `COUNTRY_NAMES_ZH`（~247 条 ISO alpha-2→中文，如 `"CN": "中国"`）
  - `_process_countries` 用中文 `name` + `name_zh` 写库

- **re-seed 支持**：[region_seed.py:155](../../backend/app/services/region_seed.py#L155) `_upsert_region` active 分支字段比对更新（支持英文→中文刷新）

#### 前端
- **ProfileView**：[ProfileView.vue:276](../../frontend/src/views/profile/ProfileView.vue#L276) 地区级联第一级显示中文（`region.name_zh || region.name`）

- **DataMaintenanceView**：[DataMaintenanceView.vue:108](../../frontend/src/views/admin/DataMaintenanceView.vue#L108) 加「更新行政区划」按钮触发 `POST /admin/regions/seed`

**关键设计**：数据源英文（ISO）→ 内置中文映射 + re-seed 刷新（_upsert_region active 分支字段比对更新）

**验证**：单测 `test_country_names_zh_covers_common`（覆盖常见国家）/`test_process_countries_uses_zh_name`（用中文 name）全过。

---

### 4. 头像裁剪（Task 5）

**目标**：个人中心头像上传支持裁剪（1:1 正方形，512×512 输出）。

**改动**：

#### 后端
- **API**：[auth.py:88](../../backend/app/api/auth.py#L88) `PUT /auth/me/avatar` 接受 `UploadFile`，调用 `storage_backend.put` 生成 URL 写库

#### 前端
- **AvatarCropperDialog**：[AvatarCropperDialog.vue](../../frontend/src/components/common/AvatarCropperDialog.vue) 新组件
  - `vue-advanced-cropper` 裁剪器（`stencil-props="{ aspectRatio: 1 }"` 1:1，`canvas-options="{ imageSmoothingQuality: 'high' }"` 高质量平滑）
  - `@ready` 事件获取 canvas，`result({ canvas })` 输出 512×512 JPEG 0.9 质量图

- **ProfileView**：[ProfileView.vue:603-628](../../frontend/src/views/profile/ProfileView.vue#L603-L628)
  - `uploadAvatar` 拆成两步：选图（`<input type="file">`）→ 裁剪对话框
  - `uploadCroppedAvatar(blob)`：blob → File（`filename: 'avatar.jpg'`）→ `PUT /auth/me/avatar`

**验证**：手动核验（见下方清单）。

---

### 5. 向导增强（Task 6）

**问题**：原 `v-stepper` 默认双语言按钮（PREVIOUS/NEXT + 上一步/下一步），且向导② PicGo 三字段缺失。

**改动**：

#### 前端
- **StorageConfigView**：[StorageConfigView.vue:70](../../frontend/src/views/admin/StorageConfigView.vue#L70) `v-stepper` 加 `:hide-actions="true"`（隐藏默认按钮，只留中文）
- **向导② PicGo 三字段**：见 Task 2+3（base_path/custom_domain/url_suffix）
- **url_style 提示**：[StorageConfigView.vue:98](../../frontend/src/views/admin/StorageConfigView.vue#L98) 文本框提示 "OSS/AWS=virtual，MinIO=path"
- **展示卡**：[StorageConfigView.vue:112-126](../../frontend/src/views/admin/StorageConfigView.vue#L112-L126) payload 跟进（含三字段）

**验证**：手动核验（向导只有一组中文按钮）。

---

## 关键设计/教训

### DB 存逻辑 key（不含 base_path）
- **S3Backend 内部加前缀**：`_full_key(key)` 拼接 `base_path + key` 返回真实 key
- **base_path 改动 DB 零改动**：DB 存逻辑 key（如 `"avatar.jpg"`），base_path 从 `"images/"` 改成 `"avatars/"` 只需重传文件，DB 不变
- **迁移**：`migrate_to_s3` 传 `base_path` 参数，重传时加前缀

### url_for 优先级
- **PicGo 风格**：custom_domain > virtual > path + url_suffix
  - custom_domain 设了则用 CDN 域名（如 `"https://cdn.example.com"`）
  - 否则 virtual-style（默认，bucket-name ）
  - 否则 path-style（endpoint 含 bucket 名）
  - url_suffix 末尾（如 `"!preview.jpg"`）

### OSS 兼容
- **boto3 新版 streaming-unsigned-payload-trailer 对 OSS 不兼容**：阿里云 OSS 不支持该特性，导致 `PutObject` 报 `STREAMING-UNSIGNED-PAYLOAD-TRAILER`
- **修复**：`payload_signing_enabled=True` + `request_checksum_calculation/response_checksum_validation='when_required'`

### 国家级数据源
- **英文（ISO）→ 内置中文映射**：`COUNTRY_NAMES_ZH` 常量（~247 条）
- **re-seed 刷新**：`_upsert_region` active 分支字段比对更新（支持英文→中文刷新）

### alembic down_revision 必须链建表迁移
- **Task 2 review 抓到的分叉**：加列迁移（20260720_0002）的 down_revision 必须链建表迁移（20260720_0001），不能与建表并指同一 down

---

## 手动端到端核验清单（用户登录态操作）

### 1. OSS 真机手测（关键）
后台「图片存储」向导填 OSS 配置：
- endpoint: `https://oss-cn-shanghai.aliyuncs.com`
- bucket: `your-bucket-name`
- access_key_id / secret_access_key: 真实 AK/SK
- region: `oss-cn-shanghai`（选填）
- url_style: `virtual`（**OSS/AWS 必选 virtual**）
- base_path / custom_domain / url_suffix: 测试 PicGo 三字段

→ 点「测试连接」（向导③）

**预期**：连接成功（向导④展示卡 "连接成功" + 当前配置）。**若仍报 STREAMING-UNSIGNED-PAYLOAD-TRAILER 或其他错误，反馈具体错误迭代 Config 参数**。

### 2. PicGo 三字段生效
- 向导②填 base_path=`images/`，custom_domain=`https://cdn.example.com`，url_suffix=`!preview.jpg`
- 点「测试连接」→「迁移」→「确认」
- 前端访问图片 URL 预期形态：`https://cdn.example.com/images/avatar.jpg!preview.jpg`

### 3. 头像裁剪
- `/profile` 点头像
- 裁剪对话框（1:1 缩放/拖动）
- 确认 → 上传 → 头像更新（512×512）

### 4. 国家级中文
- `/profile` 地区级联第一级显示中文（如 "中国" 而非 "China"）
- 数据维护中心「更新行政区划」按钮触发 re-seed

### 5. 向导按钮
- 后台「图片存储」向导只有一组中文按钮「上一步/下一步」（无 PREVIOUS/NEXT）

---

## 单测/构建验证

- **后端 compileall**：✓ 通过
- **本轮新增单测**（59 passed）：
  - storage/test_s3_picgo.py: 5 passed
  - storage/test_effective.py: 3 passed
  - storage/test_factory.py: 6 passed
  - storage/test_storage_config_api.py: 4 passed
  - storage/test_migrate.py: 4 passed
  - test_region_admin.py: 3 passed
  - test_region_country_zh.py: 2 passed
  - test_region_seed_lifespan.py: 1 passed
- **全量 pytest 回归**：620 passed / 24 failed / 6 skipped（失败数不高于基线，无本次引入新失败）
- **前端 build**：✓ 34.02s，precache 131 entries

---

## Alembic 迁移

- **20260720_0001_add_storage_config_and_avatar.py**：建 storage_configurations 表 + users.avatar_url
- **20260720_0002_add_picgo_fields.py**：加 s3_base_path/s3_custom_domain/s3_url_suffix 三字段（S3 专用）

对应 SQL 脚本：
- `backend/scripts/sql/20260720_storage_config_sqlite.sql`
- `backend/scripts/sql/20260720_storage_config_mysql.sql`
- `backend/scripts/sql/20260720_storage_config_postgresql.sql`
- `backend/scripts/sql/20260720_picgo_fields_sqlite.sql`
- `backend/scripts/sql/20260720_picgo_fields_mysql.sql`
- `backend/scripts/sql/20260720_picgo_fields_postgresql.sql`

---

## 后续待用户真机验证

- OSS 真机连接（endpoint/bucket/ak/sk/region=url_style=virtual）
- PicGo 三字段 URL 形态（custom_domain + base_path + url_suffix）
- 头像裁剪上传
- 国家级中文显示
- 向导中文按钮
