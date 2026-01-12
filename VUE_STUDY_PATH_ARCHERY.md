# Vue 学习清单（以 Archery 为 Case / 每天 1 小时）

适用人群：Vue 小白、希望“学一点就能在 Archery 里用一点”。  
目标：在 **不影响旧版页面**（`/dashboard/`）的前提下，逐步把 **Vue 版 Dashboard**（`/ui/dashboard`）做得“能用且好维护”。

---

### 你现在的项目现状（已具备）

- **旧版 Dashboard**：`/dashboard/`（Django 模板 + jQuery）
- **Vue 版入口**：`/ui/dashboard`（Vue Router）
- **Vue 专用数据接口**：`GET /dashboard/data/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`（纯 JSON）
- **静态构建输出**：`ui/` 通过 Vite build 输出到 `common/static/ui/`，静态资源走 `/static/ui/`

---

### 必备资源（“圣经优先读”）

- **Vue 3 官方文档**：`https://cn.vuejs.org/`
- **Vue Router**：`https://router.vuejs.org/zh/`
- **Vite**：`https://cn.vite.dev/`
- **TypeScript Handbook（查概念用）**：`https://www.typescriptlang.org/docs/`
- **MDN（HTML/CSS/JS）**：`https://developer.mozilla.org/zh-CN/`

视频（可选，偏跟练）：
- Vue Mastery：`https://www.vuemastery.com/`
- Vue School：`https://vueschool.io/`

---

### 运行与调试（开发环境）

后端（Django）：
- 按项目 `DEVELOPMENT_GUIDE.md` 启动（你本地环境可能用 `venv`）。

前端（Vue）：
- 开发调试：

```bash
cd /data/Archery/ui
npm run dev
```

- 产出静态文件（给 Django `/ui/*` 用）：

```bash
cd /data/Archery/ui
npm run build
```

---

### 2 周冲刺（10 天 × 每天 1 小时）

#### Day 1：Vue 基础（组件 + 响应式）
- **读**：Vue 文档「快速开始」「组合式 API 基础」
- **做（Archery）**：
  - 打开 `ui/src/pages/DashboardPages.vue`，理解 `ref()`、`v-model`、`v-if`
  - 在页面顶部加一个“当前时间范围”的展示（纯前端，不请求后端）

验收：
- 页面能显示 `startDate/endDate` 文本且随输入变化。

---

#### Day 2：TypeScript “最少够用”
- **读**：TS 的 `interface`、`type`、泛型（只要看能理解即可）
- **做（Archery）**：
  - 打开 `ui/src/types/dashboard.ts`
  - 把 `DashboardDataResponse` 读懂：哪些字段是后端给的、哪些是页面用的
  - 在 `DashboardPages.vue` 里把 `data.value` 的使用写得更严格（避免 any）

验收：
- 你能解释清楚：`DashboardDataResponse` 每个字段做什么。

---

#### Day 3：请求与错误处理（fetch / try-catch）
- **读**：MDN `fetch`、HTTP 状态码基础
- **做（Archery）**：
  - 打开 `ui/src/api/dashboard.ts`
  - 给 `fetchDashboardData` 增加更友好的错误（例如把 403 提示“无权限”）

验收：
- 没权限时前端能显示“403 无权限”，而不是一坨报错文本。

---

#### Day 4：Vue Router（页面入口与导航）
- **读**：Vue Router「基础」「history」
- **做（Archery）**：
  - 打开 `ui/src/router/index.ts`
  - 新增一个路由 `/about`（随便写个页面组件）
  - 在 `ui/src/App.vue` 里加一个简单导航（两个链接）

验收：
- `/ui/about` 能打开，且刷新不会 404（因为 Django 已做回退）。

---

#### Day 5：ECharts 最小心智（setOption）
- **读**：ECharts 入门（官方示例随便看 1 个 line chart）
- **做（Archery）**：
  - 打开 `ui/src/componets/WorkflowByDateChart.vue`
  - 理解 `onMounted / watch / dispose`
  - 把 tooltip 或 legend 做一点小改动（练手）

验收：
- 图能正常显示，改动有效。

---

#### Day 6：对齐旧版 UI（快速变“不简陋”）
- **读**：Bootstrap 栅格概念（row/col）
- **做（Archery）**：
  - 在 `ui/index.html` 引入现有 Archery CSS（bootstrap/sb-admin-2/font-awesome）
  - 用 `panel`/`row`/`col` 重排 `DashboardPages.vue` 的布局

验收：
- Vue Dashboard 看起来“像 Archery”，而不是 demo 页。

---

#### Day 7：加入 “卡片统计”（Dashboard 四个数字）
- **读**：Vue computed / 模板渲染
- **做（Archery）**：
  - 扩展后端 `DashboardDataApi`：返回 `counts`（四个数字）
  - 前端增加四个卡片展示（类似旧版 dashboard 的四块）

验收：
- Vue 页面能看到：SQL 工单数/查询工单数/用户数/实例数。

---

#### Day 8：把“时间范围输入框”换成友好的选择器
- **读**：组件拆分、props
- **做（Archery）**：
  - 新建 `ui/src/componets/DateRangePicker.vue`（先用两个 `<input type="date">` 就行）
  - `DashboardPages.vue` 使用这个组件，并在变化时触发刷新

验收：
- 不用手输 YYYY-MM-DD，也能刷新图表。

---

#### Day 9：代码整理（把能复用的抽出来）
- **读**：Vue 组件通信（props/emits）
- **做（Archery）**：
  - 把“loading + error 展示”抽成一个小组件（或 composable）
  - 把图表外壳做成 `<ChartCard title="...">...</ChartCard>`

验收：
- `DashboardPages.vue` 变短、更好读。

---

#### Day 10：加一个“权限与登录态”的最小闭环
- **读**：前端鉴权的基本思路（了解即可）
- **做（Archery）**：
  - 当接口返回 403 时，页面给出明确提示，并提供跳转到 `/login/`
  - （可选）加一个 `/api/v1/me` 之类的接口用于展示“当前用户”

验收：
- 没权限时不会“白屏”，而是给出下一步操作。

---

### 每天 1 小时怎么用（小白友好）

- **20 分钟读官方文档**
- **30 分钟照着 Archery 改一小块**
- **10 分钟写下今天学会的 3 个关键词 + 1 个疑问**

---

### 你做完后会自然掌握的能力（对照表）

- **Vue**：组件、ref/computed/watch、生命周期、模板语法
- **工程**：Vite 构建、目录拆分、TS 类型定义
- **路由**：Vue Router history、SPA 回退
- **数据**：请求封装、错误处理、权限/登录态基础
- **图表**：ECharts setOption、组件化渲染

