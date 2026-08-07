# BUGFIX：移动端 Flutter 调试失败（drift 生成代码缺失）

## 现象

`feat/mobile-app` 分支 Windows 桌面调试（`flutter run -d windows`）编译失败：

```
lib/core/database/app_database.dart(22,13): error GE5CFE876: The method 'select' isn't defined for the type 'AppDatabase'.
lib/core/database/app_database.dart(26,13): error GE5CFE876: The method 'update' isn't defined for the type 'AppDatabase'.
lib/core/database/app_database.dart(26,20): error G4127D1E8: The getter 'offlineQueue' isn't defined for the type 'AppDatabase'.
lib/core/database/app_database.dart(27,13): error G4020727C: Not a constant expression.
lib/core/database/app_database.dart(32,13): error GE5CFE876: The method 'delete' isn't defined for the type 'AppDatabase'.
```

## 根因

- [app_database.dart](mobile/lib/core/database/app_database.dart) 第 8 行 `part 'app_database.g.dart';`，drift 的 `select`/`update`/`delete`、表 getter `offlineQueue`、`OfflineQueueCompanion` 等全部由 build_runner 生成
- `mobile/.gitignore` 里 `*.g.dart` 被忽略（drift 标准做法，生成文件不入库）
- git 中无任何 `.g.dart` 文件、无 `build.yaml`（drift 有内置默认配置，不需要）
- 此环境从未跑过生成器 → `app_database.g.dart` 缺失 → 所有生成 API 未定义
- `Not a constant expression`（27 行 `const OfflineQueueCompanion(...)`）为生成代码缺失时的级联误报，生成后消失

## 修复

```bash
cd mobile
dart run build_runner build --delete-conflicting-outputs
```

76s 完成，写入 138 个输出（drift_dev 137 + riverpod_generator 若干）。

## 验证

- `app_database.g.dart` 生成成功（21.5KB）
- `flutter analyze` 通过：仅剩 3 个预先存在且与本次无关的问题（`avoid_print` info、`recipe_repository.dart` 的 unused_import / unused_element 警告）
- 原报错全部消除，可正常启动 Windows 调试

## 后续：VS Build Tools 缺 ATL 组件（flutter_secure_storage_windows 编译失败）

drift 修好后 `flutter run -d windows` 再报 C++ 错误：`error C1083: 无法打开包括文件: "atlstr.h"`（[flutter_secure_storage_windows_plugin.cpp](mobile/windows/flutter/ephemeral/.plugin_symlinks/flutter_secure_storage_windows/windows/flutter_secure_storage_windows_plugin.cpp)）。根因：`flutter_secure_storage_windows` 插件硬依赖 ATL，而 `D:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools` 的 VC 工具链（14.51.36231）缺 `atlmfc` 目录（ATL 组件未装；当时环境还发现 20:40-21:01 有一次 3.7GB 的 VS 组件安装，ATL 也是 NotSelected）。

修复（需管理员权限）：

```powershell
# 非提权会话直接调 setup.exe modify 会静默失败（无日志、UAC 弹不出），必须提权
$p = Start-Process -FilePath "C:\Program Files (x86)\Microsoft Visual Studio\Installer\setup.exe" `
  -ArgumentList 'modify','--installPath','"D:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools"',`
  '--add','Microsoft.VisualStudio.Component.VC.ATL','--passive','--norestart' `
  -Verb RunAs -Wait -PassThru
```

验证：`atlmfc\include\atlstr.h` 存在 → `flutter build windows --debug` 122s 通过产出 exe。

教训：
- Flutter Windows 插件若用 ATL（flutter_secure_storage_windows 等），VS 安装时必须勾选「适用于最新 v143 生成工具的 C++ ATL」，C++ 工具链单独装不够
- `setup.exe` 是 GUI 程序：非交互后台 + 非管理员会话调用会**静默失败不写日志**（先查 `IsInRole(Administrator)`，用 `Start-Process -Verb RunAs -Wait` 拿真实退出码）

## 教训

- drift / riverpod / freezed 项目（`*.g.dart` 入 gitignore）在**新环境 clone 后必须手动跑一次 `dart run build_runner build`**，否则生成 API 全部未定义
- 报错特征识别：「生成 API 全未定义」（select/update/delete + 表 getter + companion）+ 偶发级联的 `Not a constant expression` → 先查 `.g.dart` 是否存在，再查 pubspec 依赖，最后跑生成器
