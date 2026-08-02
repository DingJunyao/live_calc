# 粘贴导入复制模板

## 背景
快速填写页（[QuickFillView.vue](frontend/src/views/prices/QuickFillView.vue)）的「粘贴导入价格」对话框（[PasteImportDialog.vue](frontend/src/components/prices/PasteImportDialog.vue)）要求用户按 `名称 价格[/单位]` 格式粘贴文本。用户希望提供「复制空模板」：一键复制该商家全部历史商品名清单（每行「商品名 」+ 尾随空格），粘走到别处（微信/记事本/Excel）对照填好价格再粘回来。复制需兼容 http / https 部署。

## 范围决策
模板含**全部历史商品**（含近 1h 已填隐藏的），非「仅可见」——隐藏只是 UI 反重复机制，模板语义是「完整清单」，用户拍板。顺序按快速填写页面（分类 sort_order + 组内拼音），不分类别标题。

## 实现（3 处）

### 1. 新建 [utils/clipboard.ts](frontend/src/utils/clipboard.ts)（DRY 通用复制工具）
`copyText(text): Promise<boolean>`：
- 优先 `navigator.clipboard.writeText`（仅安全上下文可用：https / localhost / file，dev 的 localhost 走这条）
- `window.isSecureContext` 为 false 或 API 失败 → 降级 `document.execCommand('copy')`（临时 textarea 固定定位 + 透明 + `fontSize:16px` 防 iOS 缩放，select 后 copy 再移除）
- 返回是否成功

兼容 http 明文部署（内网 / NAS 直连）——这是现有 [InviteCodesView.copyToClipboard](frontend/src/views/admin/InviteCodesView.vue#L481) 的缺口：它裸调 clipboard、失败仅 `console.error`，http 非 localhost 直接挂。本次未改它（YAGNI，无关代码），但新工具可供后续替换。

### 2. QuickFillView 传 prop
新增 `historyProductNames` computed：基于已加载排好序的 `historyRows`（**全量**，非 `visibleHistoryRows`——后者过滤隐藏），map productName + 过滤空名。顺序天然与页面一致（`onMerchantChange` 已按 custom_sort_score → 分类 sort_order → 拼音排好），无需重排。传给 PasteImportDialog 作 `:history-product-names`。

数据来源选 prop 而非子组件自请求：避免重复打 `/merchants/{id}/product-prices`、保证顺序与页面完全一致（DRY）。

### 3. PasteImportDialog 加 UI + 逻辑
- **template**：粘贴文本框上方加「复制模板」文字按钮（`mdi-clipboard-outline`，`historyProductNames` 空时禁用）
- **二级对话框**：点击按钮 → 弹出独立 v-dialog（与主 dialog 同级，Vue 3 多根 fragment；Vuetify 各自 teleport 到 body、z-index 自管理），含只读 textarea 预览模板 + 复制按钮 + 关闭按钮
- **模板文本**：`templateText = computed(() => historyProductNames.map(n => n + ' ').join('\n'))`，每行尾随空格，方便粘走后在空格后直接填价格
- **复制反馈**：`copyTemplate()` 调 `copyText`，成功后 `copied=true`，按钮文字「复制」→「已复制」、图标 `mdi-content-copy`→`mdi-check`，2s 后恢复
- **样式**：`.template-preview` 等宽字体 + `white-space: pre`（保留尾随空格、各行对齐易读）

props 用 `withDefaults` 给 `historyProductNames: () => []` 默认空数组（向后兼容）。

## 验证
- `npm run build` 通过（22.50s，precache 131 entries，无 TS / 编译错误）
- 手动验证待做：选商家 → 打开粘贴导入 → 点「复制模板」→ 二级框弹出预览 → 点复制 → 粘到记事本确认每行「名 + 空格」；http 环境验证降级路径

## 影响面
纯前端，3 文件改动（新建 clipboard.ts + QuickFillView +computed/prop + PasteImportDialog template/script/style），后端零改动，无表结构变更。InviteCodesView 等其它复制点未动。
