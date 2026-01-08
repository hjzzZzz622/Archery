进行 Archery 的二次开发（二开），意味着你需要深入理解它如何处理 **SQL 审核、执行、实例管理以及工单流转**。Archery 是一个标准的 Django 项目，但业务逻辑比较重。

核心代码几乎都在 **`sql/`** 这个 application 目录下。以下是按照“功能模块”划分的**必读文件清单**，以及你需要深入理解它们的原因：

### 1. 核心业务引擎层 (最重要)
如果你要增加新的数据库支持，或者修改 SQL 执行/审核的底层逻辑，这部分是必须看懂的。

*   **`sql/engines/` 目录**
    *   这是 Archery 的心脏，使用了**工厂模式**来适配不同的数据库（MySQL, Redis, PostgreSQL, Oracle 等）。
    *   **`sql/engines/__init__.py`**: 定义了获取引擎实例的入口 `get_engine`。
    *   **`sql/engines/mysql.py` (或其他数据库文件)**: 具体的实现类。如果你想二开支持一个新的数据库（比如 ClickHouse），你需要参考这里的代码，继承基类并实现 `query`, `execute`, `get_all_tables` 等方法。
    *   **`sql/engines/inception.py` / `goinception.py`**: 如果你关注 SQL 审核（语法检查、回滚生成），这里封装了与 GoInception/SQLAdvisor 交互的逻辑。

### 2. 工单与流程控制层
如果你要修改工单的审批流程（例如接入飞书/钉钉审批，或者改变审批层级），看这里。

*   **`sql/models.py`**
    *   **`SqlWorkflow`**: SQL 上线工单的主表。
    *   **`QueryPrivileges`**: 查询权限申请工单表。
    *   **`Instance`**: 数据库实例配置表。
    *   **理解重点**: 表之间的关联关系（特别是 ResourceGroup 资源组的概念），以及工单的状态流转字段（`status`）。
*   **`sql/utils/workflow_audit.py`**
    *   这里控制着**工单审批流**的核心逻辑。
    *   **`audit()` 方法**: 决定了工单是自动通过、流转到下一级，还是被驳回。
    *   如果你想二开接入公司内部的 OA 系统（BPM），大概率要重写或 hook 这个文件里的逻辑。

### 3. SQL 执行与异步任务
Archery 的 SQL 执行是异步的（基于 Django-Q），不是在 HTTP 请求中直接完成的。

*   **`sql/utils/execute_sql.py`**
    *   这是**执行工单**的入口。
    *   它负责调用 `engines` 层的接口去真正的执行 SQL，处理事务，并更新工单的执行结果和日志。
    *   **难点**: 包含了大量的异常处理、进度更新逻辑和根据不同模式（自动执行/手动执行）的分支判断。
*   **`sql/utils/tasks.py`** (或 `sql/tasks.py`)
    *   Django-Q 的异步任务定义。你会看到 `@async_task` 装饰器。
    *   理解这里有助于你知道后台任务是如何被调度和重试的。

### 4. 权限与资源隔离
Archery 的权限系统比较复杂，因为它结合了 Django 的 RBAC 和自己的“资源组”概念。

*   **`sql/utils/resource_group.py`**
    *   处理**资源组（Resource Group）**的逻辑。
    *   Archery 通过资源组来隔离不同用户能看到的数据库实例。如果你发现用户看不到实例，或者想修改这种隔离策略，必须看懂这个文件。
*   **`common/utils/extend_json_encoder.py`**
    *   虽然是工具类，但处理数据序列化时经常用到，防止 json 报错。

### 5. 视图与接口 (API)
如果你要修改前端页面交互，或者开发 API 给其他系统调用。

*   **`sql/views.py`**
    *   传统的 Django Template 视图（如果不二开前端页面，这部分只需了解路由跳转）。
*   **`sql/api.py`** (或 `sql/apiv1/*.py`)
    *   **RESTful API** 接口。前端（Vue/React）主要和这里交互。
    *   如果你要增加一个按钮功能，通常需要在 `urls.py` 注册路由，并在 `api.py` 写处理逻辑。

### 6. 配置文件
*   **`archery/settings.py`**
    *   标准的 Django 配置。二开时常需要修改 `INSTALLED_APPS`（加插件）、`DATABASES`（元数据库）、`Q_CLUSTER`（异步队列配置）。

---

### 二开学习路径建议

1.  **先看 `models.py`**：弄清楚 `Instance`（实例）、`SqlWorkflow`（工单）、`ResourceGroup`（组）三者关系，这是骨架。
2.  **再看 `sql/engines/mysql.py`**：找一个简单的查询方法（如 `get_all_databases`），打断点调试，看它如何从页面请求最终流转到数据库执行命令。
3.  **最后看 `workflow_audit.py`**：这是最容易出业务逻辑 bug 的地方，理解状态机是如何变化的。
