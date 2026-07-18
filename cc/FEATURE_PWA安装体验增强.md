# FEATURE：PWA 安装体验增强（screenshots / id / display_override / protocol_handlers）

## 背景

Chrome 开发者工具 PWA 审计提示 4 条，用户全选落实：

1. 更丰富的安装 UI（screenshots）：桌面 wide + 移动 narrow 各一张
2. id 字段规范化（未指定时用 start_url 推导）
3. display-override + 窗口控件覆盖（WCO）
4. protocol_handlers 协议处理

## 改动

### 1. manifest 四项（[vite.config.ts](frontend/vite.config.ts)）

- `id: '/'`：显式应用身份，与当前 start_url 推导值一致，零破坏性。
- `display_override: ['window-controls-overlay', 'standalone']`：桌面安装版优先 WCO，回退 standalone。
- `screenshots`：桌面 wide 2240×1400 + 移动 narrow 752×1631，用户手动截图放 `public/screenshots/`。
- `protocol_handlers: [{ protocol: 'web+livecalc', url: '/?protocol-uri=%s' }]`：浏览器以 `/?protocol-uri=web+livecalc://recipe/123` 唤起应用。

### 2. WCO 全局 CSS（[App.vue](frontend/src/App.vue) style 块）

```css
@media (display-mode: window-controls-overlay) {
  header.v-app-bar { -webkit-app-region: drag; }  /* 顶部可拖拽移动窗口 */
  header.v-app-bar .v-toolbar__content {
    padding-right: calc(100vw - env(titlebar-area-x) - env(titlebar-area-width));  /* 右侧避开系统控件 */
  }
  header.v-app-bar :is(button, a, input, .v-btn, .v-field, [role='button']) {
    -webkit-app-region: no-drag;  /* 交互元素保持可点 */
  }
}
```

**放 App.vue 全局 style 不放 AppLayout**：[AppLayout](frontend/src/components/layout/AppLayout.vue) 无顶部 bar（侧边导航 + router-view），各 view 自带 v-app-bar。App.vue 全局 `header.v-app-bar` 选择器一次覆盖所有 view——而且 App.vue 原本就在管该选择器的固定定位（left 偏移随侧边栏模式），WCO 是同类规则，聚合进去最干净。

### 3. protocol 深链接解析（[App.vue](frontend/src/App.vue) onMounted）

`handleProtocolUri()` 在 `fetchUser` 之后调用，解析 `?protocol-uri=web+livecalc://type/id`，正则 `^web\+livecalc:\/\/(recipe|product|ingredient|merchant)\/(\w+)` 匹配后映射跳转：

- `web+livecalc://recipe/{id}` → `/recipes/{id}`
- `web+livecalc://product/{id}` → `/data/products/{id}`
- `web+livecalc://ingredient/{id}` → `/data/ingredients/{id}`
- `web+livecalc://merchant/{id}` → `/data/merchants/{id}`

`router.replace(target)` 跳转并顺带清掉 query。详情路由均 requiresAuth，放 fetchUser 后确保登录态就绪让守卫放行。

## 关键决策

- **WCO 全局 CSS 而非组件级**：因无统一顶部 bar，全局选择器覆盖所有 view 的 v-app-bar。
- **protocol 放 onMounted fetchUser 后**：跳详情需登录态。
- **screenshots 尺寸回填实际值**：读 PNG IHDR（offset 16/20 readUInt32BE）拿真实 2240×1400 / 752×1631，非预估占位。

## 验证

- build 通过（16.16s），PWA precache 112 → 114（screenshots 两张纳入缓存）。
- screenshots 比例正确（wide 横 / narrow 竖），Chrome 审计两条「更丰富安装 UI」应消除。

## 遗留/注意

- 截图体积偏大（desktop 1.7MB / mobile 1.1MB），precache 体积随涨；生产前可用 `@vite-pwa/assets-generator` 自带的 sharp 压缩（无需新装依赖）。
- protocol_handlers 偏演示性（本应用无真实 `web+livecalc://` 链接源），合规展示协议处理能力。
- WCO 仅桌面安装版 Chrome/Edge 生效，移动端无影响。
- 无表结构变更，纯前端。
