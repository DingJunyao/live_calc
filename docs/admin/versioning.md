# 版本管理

版本号与应用身份的唯一来源是仓库根目录的 `app-info.json`，包括名称、短名、版本、简介、版权、GitHub 仓库、项目主页和作者主页。

## 改版本号

1. 编辑根目录 `app-info.json`，修改 `version` 字段。
2. 在仓库根目录执行：

```powershell
python scripts/sync_versions.py
```

3. 提交变更。

`scripts/sync_versions.py` 会把版本号同步到：

- `frontend/package.json`
- `frontend/package-lock.json`
- `backend/pyproject.toml`

其余使用方无需手动改：前端构建（Vite）和 PWA manifest 直接读 `app-info.json`；后端 `APP_INFO` / `__version__`、FastAPI 版本号、数据导出 manifest 也直接读同一份文件。Docker 构建的两个阶段都已拷贝 `app-info.json`，容器构建会自动生效。

> Docker 部署时，改完版本号需要重新构建镜像。
