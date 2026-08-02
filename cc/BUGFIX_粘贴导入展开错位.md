# 粘贴导入展开待处理项视口错位（移动端）

## 问题

移动端快速填写「粘贴导入」对话框（[PasteImportDialog](frontend/src/components/prices/PasteImportDialog.vue)），点击待处理项（unmatched）展开内联编辑面板时，**视口剧烈下跳**——从点击行跳到列表下方/底部，当前行连同展开面板被挤出可视区，要往上翻才看得到。桌面端无此问题。

## 七轮拉锯（弯路值得记录）

1. `scrollIntoView({ block: 'start' })` → 甩到顶部，用户要原位
2. scrollTop 锁定（rAF） → 没生效
3. `table-layout: fixed`（加在 `.paste-preview-table`） → 没生效 + 名称列太窄
4. `overflow-anchor: none` → 没生效（不是 anchoring）
5. blur focusin 拦截 → 那次混了手动滚动惯性，误判
6. rAF 对冲 scrollTop → 没生效（操作的元素错）
7. fixed v2（重分配列宽） → 仍没生效（选择器还是错的）

## 关键诊断证据

- **第一轮 capture scroll 诊断**：`scroll @ 44ms, .v-card scrollTop=909` → 误以为是展开引起的 scroll。后来用户澄清那是**点击前手动滚动找项目时的惯性**，姐姐被误导了几轮。
- **scrollTop setter hook**：scrollTop 不是 JS 设的 → 排除 JS 主动赋值
- **scrollIntoView/scrollTo hook**：无 JS 方法调用 → 排除 JS 方法触发
- **blur focusin 实验**：scroll 照发生 → 排除 focus（但那次也混了手动滚动）
- **全量枚举诊断（决定性）**：点击展开后**没有任何 scroll 事件**触发 → 视口「跳」根本不是 scroll，是 **reflow 重排**
- 用户两次坚持「名称列宽度会变化」+ 候选容器列表有 `.v-table__wrapper` → 直指真相

## 真正根因

Vuetify v-table 的结构是 `.paste-preview-table (外层 div) > .v-table__wrapper > <table>`。

前几轮写的 `.paste-preview-table { table-layout: fixed }` 加在了**外层 div** 上——**`table-layout` 属性对 div 完全无效，只有作用在 `<table>` 元素上才生效**。所以 fixed **从头到尾没生效过**，`getComputedStyle(.paste-preview-table).tableLayout` 查的是 div（无意义），难怪列宽还在变、几次「验证 fixed 没用」全是空打。

因果链：
> fixed 没生效 → 列宽 auto → 展开 autocomplete 面板撑宽名称列 → 其他列被挤窄 → 价格/数量等内容换行 → 上方行变高 → **reflow 把当前行（如分切南瓜）挤出可视区**

reflow 不是 scroll，所以：
- 无 scroll 事件（诊断铁证）
- `overflow-anchor: none` 无效（不是 anchoring）
- rAF 对冲 scrollTop 无效（scrollTop 根本没变，是内容位移）

## 最终修复

[PasteImportDialog.vue](frontend/src/components/prices/PasteImportDialog.vue) 单文件：

1. **`:deep(table) { table-layout: fixed }`** —— 穿透到 `<table>` 元素，fixed 真正生效，列宽钉死，展开/折叠都不再 reflow。**这是核心**。
2. **列宽重新分配**：图标 28 + 价格 56 + 数量 48 + 单位 44 = 176px（原先 90+70+70+36=266 太占），移动端给名称列留约 150px，桌面端约 540px，不再像初版 fixed 那样挤成 74px
3. **展开态 `colspan="5"`** —— 整行合并成一个撑满表格宽度（~328px）的大格，面板有充足空间放两个 autocomplete + 按钮；避免被 fixed 列宽截断。按钮组加 `flex-wrap`，窄屏时取消按钮自动换行
4. **展开态顶部摘要行** —— 左边商品名（加粗）+ 右边 `价格 · 数量单位`（浅色小字），把折叠时藏掉的原名和价格上下文补回来，让用户知道在编辑哪条

附带：撤掉所有 scroll 对抗 hack（openEditor 回归朴素四行），`overflow-anchor: none` 留在 `.paste-card` 作双保险（无害）。

## 验证

- `getComputedStyle(document.querySelector('.paste-preview-table table')).tableLayout === 'fixed'`（之前是 `'auto'`，fixed 没生效）
- 展开「分切南瓜」→ 面板就地展开、不跳下方、下拉框提示与按钮文字完整、顶部显示商品名和价格摘要
- build 通过（17.45s，precache 131 entries 不变）。纯前端单文件，无表结构变更。

## 教训

- **`table-layout` 必须作用在 `<table>` 元素上**。Vuetify v-table 的 class 是外层 div，要 `:deep(table)` 穿透到内部 table 才有效——这个坑让姐姐空转了七轮。
- **reflow 重排不触发 scroll 事件**。视口「跳」如果没 scroll 事件支撑，是内容位移不是滚动，所有 scroll 对抗手段（anchoring、scrollTop 锁定、scrollIntoView）都无效，得从布局重排源头治。
- **诊断要剔除「手动滚动惯性」干扰**。移动端用户点击前必然先滚到目标行，那段滚动日志极易被误当成点击触发；让用户「滚到位完全停稳再挂诊断再点击」才能拿到干净证据。
- **用户的直观观察值得重视**。用户两次指出「列宽变化」，姐姐前几轮急着用「测试通过」否定，走了大弯路——凡用户反复强调的视觉细节，多半是破案钥匙。
