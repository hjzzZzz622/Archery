# Archery 二开说明 / 学习路径（Development Guide）

这份文档的目标不是“如何贡献代码”，而是帮助你在做 Archery 的二次开发（简称二开）时，快速建立**系统心智模型**、定位**关键入口**、并能按场景找到“从哪改”。

> Archery 是标准的 Django 项目，但业务逻辑较重；核心业务代码主要集中在 `sql/` app 下。

---

## 0. 你可能的二开目标（先选一个）

- **新增/适配新的数据库类型**：增加 engine，补齐查询/审核/执行能力。
- **改工单审批流**：自动通过/驳回策略，审批节点与通知对接（OA/IM）。
- **改工单执行链路**：执行模式、结果落库、回滚、异常处理、进度与重试。
- **改资源隔离/权限策略**：资源组（ResourceGroup）可见性与审计人策略。
- **新增页面/按钮/接口**：从 URL → View/API → 业务函数 → 模型/引擎的链路改动。

如果你不确定目标，从 **第 2 节（代码地图）** 开始。

---

## 1. 关键概念速览（先把词对齐）

- **Instance（实例）**：数据库实例配置，字段在 `sql/models.py` 的 `Instance`；数据库类型由 `db_type` 决定（`DB_TYPE_CHOICES`）。
- **Engine（引擎）**：对不同数据库的适配层，位于 `sql/engines/`。通过 `sql/engines/__init__.py:get_engine(instance)` 按 `instance.db_type` 选择。
- **Workflow（工单）**：SQL 上线/变更工单主模型是 `sql/models.py:SqlWorkflow`（以及查询权限等其它类型工单）。
- **审批流（Audit）**：审批流与状态机在 `sql/utils/workflow_audit.py`（你会看到 `AuditV2`、节点定义、合法操作等）。
- **异步执行（Django-Q）**：工单执行不是在 HTTP 请求里同步完成，而是提交任务到队列；执行入口与回调在 `sql/utils/execute_sql.py`，任务定义常在 `sql/utils/tasks.py`。
- **资源组（ResourceGroup）**：用于隔离“谁能看到哪些实例/工单”，相关逻辑在 `sql/utils/resource_group.py`（偏规则/计算）以及 `sql/resource_group.py`（偏接口/视图）。

---

## 2. 代码地图：从入口到核心（最常用）

### 2.1 URL 入口在哪里？

- **全站 URL 汇总**：`archery/urls.py`
  - Web 页面（Django 模板）走：`path("", include(("sql.urls", "sql"), ...))`
  - REST API 走：`path("api/", include(("sql_api.urls", "sql_api"), ...))`

### 2.2 Web（页面/按钮）入口怎么找？

从 `sql/urls.py` 反查到具体函数：

- 大量页面入口在 `sql/views.py`
- 工单相关“列表/执行/定时/回滚”等入口分布在 `sql/sql_workflow.py` 与 `sql/views.py`
- 查询、慢日志、归档、资源组等模块分别在 `sql/query.py`、`sql/slowlog.py`、`sql/archiver.py`、`sql/resource_group.py` 等

**实战建议**：你要改一个页面按钮，先在 `sql/urls.py` 找 path，再跳到对应函数，沿着函数里调用链往下追到 `utils/` 或 `engines/`。

### 2.3 API（REST）入口怎么找？

REST API 入口在 `sql_api/urls.py`（默认挂载在 `/api/` 下），典型包括：

- 用户/组/资源组：`sql_api/api_user.py`
- 实例/隧道/RDS：`sql_api/api_instance.py`
- 工单（校验/审批/执行/日志）：`sql_api/api_workflow.py`
- OpenAPI 文档：`/api/schema/`、`/api/swagger/`、`/api/redoc/`

---

## 3. 学习路径（按时间/按任务）

### 3.1 30 分钟：先跑通“请求 → 执行”的链路

- 从 `sql/urls.py` 找一个工单入口（例如执行/审批相关），定位到处理函数
- 跳到 `sql/utils/workflow_audit.py` 看审批流如何决定状态与操作合法性
- 跳到 `sql/utils/execute_sql.py` 看异步执行如何落库与写日志
- 最后看 `sql/engines/__init__.py:get_engine` 理解 engine 是如何按 `db_type` 选择的

### 3.2 1 天游览：把“骨架三件套”看懂

- **`sql/models.py`**：`Instance`、`SqlWorkflow`、`ResourceGroup`、`WorkflowAudit/WorkflowLog`
- **`sql/engines/`**：挑你最熟的一个数据库（如 `mysql.py`）看查询/执行/元数据方法
- **`sql/utils/workflow_audit.py`**：把状态、节点、自动通过/驳回逻辑过一遍

### 3.3 1 周能改需求：按模块补齐知识

- **权限/资源组**：`sql/utils/resource_group.py` + `sql/resource_group.py`
- **执行与队列**：`sql/utils/execute_sql.py` + `sql/utils/tasks.py` + `archery/settings.py:Q_CLUSTER`
- **审计/日志/通知**：`sql/audit_log.py`、`sql/notify.py`、`sql/models.py:WorkflowLog`

---

## 4. 常见二开场景：从哪改（高频清单）

### 4.1 新增一个数据库类型（例如新增 FooDB）

你通常需要改动/新增这些点（按“最小闭环”排序）：

- **实现 engine**：在 `sql/engines/` 新增 `foodb.py`，实现你需要的能力（查询、执行、元数据等）
- **启用 engine**：`sql/engines/__init__.py` 的 `get_engine_map()` 依赖 `settings.ENABLED_ENGINES` / `settings.AVAILABLE_ENGINES`
- **让实例可选择该类型**：`sql/models.py:DB_TYPE_CHOICES` + `Instance.db_type`
- **补齐页面/API 的实例创建校验**：Web 侧在 `sql/instance.py`/相关模块；API 侧在 `sql_api/api_instance.py`

> 经验：不要一上来实现“所有能力”。先跑通“查询 + 连接测试 + 最小执行”，再逐步补数据字典/慢日志/会话管理等高级能力。

### 4.2 改工单审批流（自动通过/多级/对接外部 OA）

核心入口：

- **审批流核心**：`sql/utils/workflow_audit.py`
  - 节点与可执行动作：`SUPPORTED_OPERATION_GRID`
  - 新版审批对象：`AuditV2`（用于解析审批节点、当前节点、自动通过/驳回等）

你通常会做的改动：

- 改“自动通过/自动驳回”的策略（例如基于 `ReviewResult` 的 warning/error 处理）
- 改“节点如何生成”（按资源组、实例、工单类型、提交人等维度决定）
- 加 hook：在通过/驳回/流转时调用外部系统（建议封装成独立模块，避免把网络 I/O 写死在核心流程里）

### 4.3 改工单执行链路（异步、落库、回滚、异常）

核心入口：

- **执行入口与回调**：`sql/utils/execute_sql.py`
  - `execute(workflow_id, user=None)`：进入执行阶段、写日志、选择 engine、提交执行
  - `execute_callback(task)`：异步回调落库、更新状态、通知、清理缓存等

你改执行链路时最常踩的坑：

- **状态机约束**：代码会校验工单状态，避免重复执行/重复回写（常见于回调重试）
- **并发与锁**：执行阶段使用 `select_for_update()` 防止重复执行
- **缓存**：DDL 工单结束会清理 Redis key（例如 `*insRes*`），避免实例资源缓存不一致

### 4.4 改资源隔离/权限策略（看不到实例/工单）

优先看：

- `sql/utils/resource_group.py`：计算“用户属于哪些组/有哪些权限”的核心逻辑
- `sql/resource_group.py`：资源组相关的接口/页面交互入口

排查思路：

- 先确认用户/组（Django `Group`）关系是否符合预期
- 再看“资源组 → 实例/审计人”的关联关系是否正确
- 最后排查是否有缓存导致的“数据已改但页面不刷新”

### 4.5 新增一个 API（给外部系统调用）

建议优先走 `sql_api/`：

- 在 `sql_api/urls.py` 注册路径
- 在 `sql_api/api_*.py` 增加 APIView（或复用 serializer/permission/filter）
- 需要 OpenAPI 文档时，关注 `/api/schema/` 与 swagger/redoc 页面

---

## 5. 调试与排错（建议收藏）

### 5.1 从一个现象快速定位到文件

- **页面点击后报错/无响应**：从 `sql/urls.py` → 对应模块（`views.py` / `sql_workflow.py` / `query.py` ...）
- **审批流不流转/按钮不可点**：`sql/utils/workflow_audit.py`（节点生成、合法操作、当前节点）
- **执行卡住/状态不变**：`sql/utils/execute_sql.py` + `sql/utils/tasks.py` + `archery/settings.py:Q_CLUSTER`
- **实例连接失败/查询异常**：对应 engine（`sql/engines/<db>.py`）+ `sql/engines/__init__.py:get_engine`
- **用户看不到实例**：`sql/utils/resource_group.py` + `sql/resource_group.py`

### 5.2 快速确认 Django-Q 状态（有 API）

REST API 里存在调试/信息端点（见 `sql_api/urls.py`）：

- `/api/info`
- `/api/debug`

如果你发现“工单一直排队/没有回调写入”，优先确认队列与 worker 是否运行、配置是否正确。

---

## 6. 必读文件清单（保留自旧文档，并按二开场景组织）

### 6.1 核心业务引擎层（新增数据库/改执行底座必看）

- `sql/engines/`
  - `sql/engines/__init__.py`: `get_engine()` / engine 启用机制
  - `sql/engines/mysql.py`（或其它数据库引擎）: 具体实现参考
  - `sql/engines/goinception.py`: 审核/执行相关的适配封装

### 6.2 工单与流程控制层（改审批流必看）

- `sql/models.py`
  - `SqlWorkflow`: SQL 上线工单主表
  - `QueryPrivilegesApply`: 查询权限申请工单表
  - `Instance`: 数据库实例配置表
- `sql/utils/workflow_audit.py`
  - 审批流核心逻辑（自动通过、流转到下一级、驳回等）

### 6.3 SQL 执行与异步任务（改执行链路必看）

- `sql/utils/execute_sql.py`: 执行工单入口 + 回调落库
- `sql/utils/tasks.py`: Django-Q 任务定义与调度相关

### 6.4 权限与资源隔离（看不到实例/想改隔离策略必看）

- `sql/utils/resource_group.py`: 资源组核心逻辑

### 6.5 入口与路由（找“从哪进来”必看）

- `archery/urls.py`: Web 与 API 的总入口
- `sql/urls.py`: Web 路由汇总（大量二开需求从这里定位入口）
- `sql_api/urls.py`: REST API 路由汇总


## 7. Mongo Altas


```shell
mongosh "mongodb+srv://cluster0.kppybvl.mongodb.net/" --apiVersion 1 --username junejhuang --password p3Y5mm8zCUXaFZuS
```

## 20260112
### 1) `chart_dao = ChartDao()` 里的 `ChartDao()` 是什么？

`ChartDao` 是一个 **“专门拿来查 Dashboard 统计数据的类”**（DAO = Data Access Object，数据访问对象）。

- 它在：`common/utils/chart_dao.py`
- 它内部用 `django.db.connection` 直接执行 SQL（比如查 `sql_workflow`、`query_log` 等表），返回 `rows`（结果行）和 `column_list`（列名）。

你可以把它理解成：**“Dashboard 用的查询工具箱”**。

---

### 2) `wf_dict = {row[0]: int(row[1]) for row in wf_rows}` 在干什么？

这是 Python 的 **字典推导式**：把“列表形式的查询结果”变成“方便查找的字典”。

- `wf_rows` 长这样（示例）：  
  `[( '2026-01-01', 3 ), ( '2026-01-02', 0 ), ( '2026-01-05', 7 )]`
- `wf_dict` 会变成：  
  `{'2026-01-01': 3, '2026-01-02': 0, '2026-01-05': 7}`

为什么要这样做？
- Dashboard 需要一条连续日期轴 `dates = ['2026-01-01','2026-01-02',...,'2026-01-12']`
- 但数据库查询结果可能 **缺某些日期**（比如那天没有工单就不会返回那天）
- 所以后面会做：`counts = [wf_dict.get(day, 0) for day in dates]`  
  意思是：**每一天都要有数字，没有就补 0**，这样画图才不会“缺点/错位”。

---

### 3) 为什么 GET 接口不需要 CSRF？

CSRF 主要防的是：**别的网站诱导你在“已登录状态”下，对你的系统发起“有副作用的操作”（比如转账/改密码/提交工单）**。

- **GET** 按 HTTP 约定应该是“只读、无副作用”，所以 Django 默认一般 **不强制**对 GET 做 CSRF 校验。
- **POST/PUT/DELETE** 这类会“改数据”的请求，才需要 CSRF Token 来确认“这真是从你的网站页面发起的”。

注意：即使 GET 不需要 CSRF，**权限依然会拦**（你这里用了 `@permission_required`），没权限照样 403。

---

### 4) `.ts` 后缀的文件是什么？如何学习？

`.ts` 是 **TypeScript** 文件。

- TypeScript = “JavaScript + 类型系统”
- 你写的时候就能声明：这个字段必须是 `string`、那个必须是 `number[]`
- 好处：**写错字段名/类型不对，编辑器和编译器会提前提醒你**（对小白非常友好）

学习建议（最少路线）：
- 先只掌握三件事就够写业务了：
  - `type` / `interface`（描述数据结构）
  - 基本类型：`string/number/boolean/Array`
  - 可选字段：`foo?: string`
- 然后在每个接口请求的返回值上都写类型（像 `DashboardDataResponse` 这样）。

---

### 5) Vue 文件怎么看懂？语法要懂哪些？

Vue 单文件组件（`.vue`）一般分 3 块：

- `<template>`：写页面结构（类似 HTML，但可以用 `v-if`、`v-for` 这类指令）
- `<script setup lang="ts">`：写逻辑（变量、请求、事件函数）
- `<style>`：写样式（你当前组件里没写也正常）

你现在 `DashboardPages.vue` 里，你主要需要懂：
- **`ref()`**：声明“会变的变量”（响应式）
- **`v-model`**：输入框与变量双向绑定
- **`v-if`**：条件渲染（有数据才显示图表）
- **`@click="load"`**：点击按钮调用函数

这些掌握了就能做很多页面。

---

### 6) ECharts 是什么？

ECharts 是一个 **前端图表库**（Apache ECharts）。

你给它：
- x 轴数据（dates）
- y 轴数据（counts）
- 图表类型（line/bar/pie）

它就帮你画出漂亮的图，并支持缩放、tooltip、响应式 resize 等。

---

### 7) 这种方案相比之前有什么区别？

以前（Archery 旧前端）：
- 后端（pyecharts）把图画好 → 返回一段 HTML/JS → 模板直接塞进页面（`{{ chart.xxx|safe }}`）
- 前端基本是“展示”，交互用 jQuery 做一点点刷新

现在（给 Vue 的新接口）：
- 后端只返回 **纯数据 JSON**（dates/counts）
- 前端（Vue + ECharts）负责 **渲染图表**
- 优点（对重构最关键）：
  - 前后端职责更清晰：后端管数据，前端管展示
  - Vue 端更容易做交互（切日期范围、局部刷新、loading、错误处理）
  - 不依赖后端下发 `<script>` 字符串（更安全、更可控）

---

如果你愿意，我可以拿你这条链路再讲一次“从浏览器点击刷新 → 到数据库查数据 → 回到图表更新”的完整流程，用 10 行左右的步骤让你建立直觉。