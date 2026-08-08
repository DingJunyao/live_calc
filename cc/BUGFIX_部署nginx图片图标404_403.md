# 部署后图片 404 / 图标 403 修复

部署到 Synology NAS（192.168.100.3:6483，all-in-one 单容器）后两个独立问题：
- `/api/v1/images/avatars/xxx.jpg` 等图片 **404**（连 307 重定向都没有）
- `/logo.svg`、`/favicon.ico`、`/pwa-*.png`、`/apple-touch-*`、`/maskable-*` 等 `frontend/public/` 源文件 **403**；同目录 vite 生成的 `/assets/*.js`、`*.css` 却正常 200。

## 根因（两个独立，都藏在容器化部署配置里）

### 根因 A：nginx 正则 location 截走了 /api 下的媒体请求（图片 404）

[default.conf.template](../deploy/nginx/default.conf.template) 原配置：

```nginx
location /api/ { proxy_pass ${BACKEND_URL}; ... }          # 普通前缀
location ~* \.(?:js|css|...|jpg|png|svg|ico|webp|...)$ {   # 正则
    expires 30d; add_header Cache-Control "public, immutable";
    try_files $uri =404;
}
```

nginx location 匹配优先级：`=` > `^~` > 正则(`~`/`~*`) > 普通前缀。**正则优先于普通前缀**。

所以 `/api/v1/images/avatars/x.jpg` 因带 `.jpg` 后缀被**正则 location 截走**，nginx 拿这个 URI 去 `root /usr/share/nginx/html` 下找 `api/v1/images/avatars/x.jpg` → 不存在 → `=404` → **404**。请求**根本没到后端**的 `serve_image`（[main.py:579](../backend/app/main.py#L579)，必返 307）。

`/api/v1/static/images/*.jpg` 同理被截（StaticFiles 挂载路径也带 .jpg）。

dev 模式走 vite proxy（按路径前缀转发、不看后缀），从不经过这套 nginx，故从未暴露。

### 根因 B：public 源文件 COPY 进容器后权限不可读（图标 403）

`frontend/public/` 下的 logo.svg / favicon.ico / pwa-*.png 等从 **Windows 构建上下文** `COPY frontend/ ./` 进 Linux 容器，权限可能不可读。vite build 把它们原样复制到 dist 根，**保留了这个坏权限**；而 vite/rollup 在容器内**新生成**的 `dist/assets/*.js|css` 是 node umask 022 → 644，权限正常。

nginx 处理静态文件：`try_files` 用 stat 判定文件存在（stat 不检查读权限）→ 内部重写 → `ngx_http_static_module` 实际 open() 读取 → **读权限不足 → 403 Forbidden**。（try_files 的 `=404` 只在 stat 失败/文件不存在时触发，所以是 403 而非 404。）

对比证据坐实规律：所有 public 源文件 403、所有 assets 生成文件 200，同在 `/usr/share/nginx/html/` 同一目录、同一 location 处理，差异只能在文件自身权限。

## 证据链（Phase 1 远程 curl，ssh dsm、免 docker）

| 请求 | 结果 | 说明 |
|---|---|---|
| `/` | 200 text/html | 首页正常（nginx serve index.html） |
| `/index.html` | 200 | 同上 |
| `/assets/index-DjRTC1Nc.js` | **200** | vite 生成，权限正常 |
| `/assets/index-CKWF5jwO.css` | **200** | 同上 |
| `/api/v1/auth/config` | **200 application/json** | 非媒体后缀 → `/api/` 前缀正常反代到后端 |
| `/api/v1/images/avatars/77cd...jpg` | **404**（nginx HTML，146B） | `.jpg` 被正则截走，没到后端、没 307 |
| `/api/v1/static/images/avatars/77cd...jpg` | **404** | 同上 |
| `/logo.svg` `/favicon.ico` `/pwa-192x192.png` `/apple-touch-icon-180x180.png` `/maskable-icon-512x512.png` | **全 403** | public 源文件权限不可读 |

关键对比：`/api/v1/auth/config`（非图片）200 而 `/api/v1/images/*.jpg` 404 —— 证明 `/api/` 前缀对非媒体正常、媒体后缀被正则截走，坐实根因 A。

宿主文件状态（排除「文件没部署」嫌疑）：
- `/volume1/server/livecalc/backend/static/images/avatars/77cd0ebf6fb04cf5ad8f81ea4772a120.jpg` **存在**（77557B），recipes 下数百张图都在
- DB `storage_configurations`：`backend=local`（虽填了 S3/OSS 参数但 backend 字段仍是 local），所以 `url_for` 返 `/api/v1/static/images/<key>`，serve_image 307 跳这里——文件在本地、配置 local，链路本应通，纯被 nginx 挡在前面

## 修复

### 修复 A：[default.conf.template](../deploy/nginx/default.conf.template)

`location /api/` → `location ^~ /api/`。`^~` 使前缀匹配命中后**不再检查正则**，所有 `/api/*`（不管后缀）一律反代到后端。一行加 `^~`。

```nginx
# ^~ 提升前缀优先级至正则之上：否则下方 ~* \.(jpg|png|svg|...)$ 会截走
# /api/v1/images/*.jpg、/api/v1/static/images/*.jpg 等带媒体后缀的请求
location ^~ /api/ {
```

### 修复 B：[Dockerfile](../Dockerfile) frontend-builder stage

`RUN npm run build` → `RUN npm run build && chmod -R a+rX dist`。
- `a+r`：所有文件可读（修 public 源文件 403）
- `a+X`（大写 X）：只给**目录**加可遍历位，文件不加执行位（安全）
- 放 builder stage 而非各 runtime target，all-in-one 与 frontend target 都受益（DRY）；vite 生成的 assets 本就 644，chmod 无副作用

两处都加注释说明 why（对齐既有注释风格）。

## 验证（待用户在 NAS rebuild 后执行）

```bash
ssh dsm
cd /volume1/server/livecalc
# 同步改动（git push+pull 或 scp 两个文件）
sudo docker compose build app      # 重建（含前端 npm build + chmod + 新 nginx 配置）
sudo docker compose up -d          # 用新镜像重启
# 验证
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:6483/logo.svg                         # 期 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:6483/favicon.ico                       # 期 200
curl -sIL http://localhost:6483/api/v1/images/avatars/77cd0ebf6fb04cf5ad8f81ea4772a120.jpg        # 期 307 → 200
```

快速临时验证（不 rebuild，直接改运行中容器、确认修复有效后再 rebuild 持久化）：
```bash
sudo docker exec livecalc sed -i 's|location /api/ {|location ^~ /api/ {|' /etc/nginx/conf.d/default.conf
sudo docker exec livecalc chmod -R a+rX /usr/share/nginx/html
sudo docker exec livecalc nginx -s reload
# curl 验证同上；确认后务必同步代码 + rebuild 才能持久（容器重建会丢临时改动）
```

## 教训

- **nginx location 优先级**是经典坑：给静态资源做长缓存正则 `~* \.(js|css|png|...)$` 时，它会把**所有**带这些后缀的请求截走，包括 `/api/` 下的媒体。API 前缀必须用 `^~` 或 `=` 提升优先级，否则 API 里的图片/资源端点全被吞。
- **dev/prod 差异盲区**：dev 走 vite proxy（按前缀转发不看后缀）、prod 走 nginx（location 优先级敏感），两者行为差异让这类 nginx 配置 bug 在 dev 永远测不出来。容器化部署后必须用真实 prod 路径（nginx）端到端验证一次媒体链路。
- **Windows→Linux COPY 权限**：`COPY` 从 Windows 构建上下文复制文件进 Linux 容器，文件权限可能不可读（NTFS 无 unix mode，Docker 赋默认值不稳定）。前端构建末尾统一 `chmod -R a+rX dist` 是稳妥兜底，与具体源权限值无关。
- **403 vs 404 的信息量**：try_files 的 `=404` 只在 stat 失败时触发；文件存在但不可读会走到 static 模块 open 失败 → 403。所以「同目录 js 200、svg 403」直接指向文件级权限差异，而非 location/路径问题。
