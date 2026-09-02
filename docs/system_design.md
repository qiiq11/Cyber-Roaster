# Cyber-Roaster 系统设计文档

> 基于 AI 的幽默代码评审与梗图生成工具 · 系统级三大模型（需求 / 结构 / 行为）

- **版本**：1.0.0
- **技术栈**：FastAPI（后端） + React/Vite（前端） + SQLite（开发库） + OpenAI 兼容 LLM
- **文档约定**：所有架构图使用 Mermaid 语法；所有内容使用简体中文。

---

## 目录

1. [系统概览](#系统概览)
2. [需求模型](#需求模型)
   - 2.1 用例图
   - 2.2 数据流图（DFD）
3. [结构模型](#结构模型)
   - 3.1 领域类图
   - 3.2 ER 图
4. [行为模型](#行为模型)
   - 4.1 系统时序图
   - 4.2 状态机图
5. [技术架构与关键决策](#技术架构与关键决策)
6. [非功能需求](#非功能需求)

---

## 系统概览

Cyber-Roaster 是一个「幽默代码评审 + 梗图生成」的开发者娱乐与效率工具：

1. 用户提交代码片段（或 GitHub 仓库 + Commit SHA）。
2. 后端调用 OpenAI 兼容 LLM，生成毒舌但善意的评审（`roast_text`、`chaos_score`、`suggestions`）。
3. 后端将评审记录落库，并提供统计与梗图（四格漫画）生成能力。
4. GitHub Webhook 可在 Push 事件后自动触发评审，实现持续集成式「代码吐槽」。

```mermaid
flowchart LR
    U[用户] -->|提交代码 / 仓库| FE[React 前端]
    FE -->|HTTP REST| BE[FastAPI 后端]
    BE --> LLM[OpenAI 兼容 LLM API]
    BE --> DB[(SQLite 数据库)]
    BE --> GH[GitHub API]
    GH -->|Webhook Push 事件| BE
    BE -->|生成 PNG| FS[静态文件存储]
    FE -->|下载梗图| FS
```

---

## 需求模型

### 2.1 用例图

```mermaid
flowchart TD
    subgraph 系统边界["Cyber-Roaster 系统"]
        UC1["提交代码评审<br/>(/roast)"]
        UC2["查看统计<br/>(/stats)"]
        UC3["分析 GitHub 提交<br/>(/github/analyze)"]
        UC4["生成梗图<br/>(/meme)"]
        UC5["接收 Webhook 自动评审<br/>(/webhook/github)"]
        UC6["生成评审内容"]
    end

    User((用户)) --> UC1
    User --> UC2
    User --> UC3
    User --> UC4

    LLM((LLM API)) -.被调用.-> UC6
    Webhook((GitHub Webhook)) --> UC5

    UC1 -.依赖.-> UC6
    UC3 -.依赖.-> UC6
    UC5 -.依赖.-> UC6
    UC4 -.依赖.-> UC1
```

### 2.2 数据流图（DFD）

```mermaid
flowchart LR
    subgraph 外部实体
        U1[用户]
        U2[GitHub Webhook]
        U3[LLM API]
    end

    subgraph 进程
        P1[评审处理<br/>roast_service]
        P2[GitHub 拉取<br/>github_client]
        P3[梗图生成<br/>meme_generator]
        P4[统计聚合<br/>stats_service]
    end

    subgraph 数据存储
        D1[(analyses)]
        D2[(commits)]
        D3[(memes)]
    end

    U1 -->|代码片段| P1
    U2 -->|Push 事件| P2
    P2 -->|Diff 文本| P1
    P1 -->|prompt| U3
    U3 -->|评审结果| P1
    P1 -->|评审记录| D1
    P2 -->|提交记录| D2
    P1 -->|评审结果| P3
    P3 -->|梗图记录| D3
    P4 -->|读取| D1
    P4 -->|读取| D2
    P4 -->|读取| D3
    P4 -->|统计概览| U1
    P3 -->|PNG| U1
```

---

## 结构模型

### 3.1 领域类图

```mermaid
classDiagram
    class AnalysisRecord {
        +int id
        +str code_hash
        +str language
        +int code_length
        +str roast_text
        +int chaos_score
        +str suggestions
        +str status
        +datetime created_at
    }
    class Commit {
        +int id
        +str repo
        +str commit_sha
        +int total_additions
        +int total_deletions
        +int analysis_id
        +datetime created_at
    }
    class Meme {
        +int id
        +int analysis_id
        +str png_path
        +datetime created_at
    }
    class RoastService {
        +roast(request) AnalysisRecord
        +get(id) AnalysisRecord
        +attach_commit(...) Commit
    }
    class StatsService {
        +get_summary() dict
    }
    class LLMClient {
        +generate_roast(code, lang) dict
        +available bool
    }
    class GitHubClient {
        +get_commit_diff(repo, sha) dict
    }
    class MemeGenerator {
        +generate_meme_png(analysis) bytes
    }

    AnalysisRecord "1" o-- "0..*" Commit : 关联
    AnalysisRecord "1" o-- "0..*" Meme : 关联
    RoastService --> LLMClient : 调用
    RoastService --> AnalysisRecord : 持久化
    RoastService --> Commit : 关联
    StatsService --> AnalysisRecord : 统计
    StatsService --> Commit : 统计
    StatsService --> Meme : 统计
```

### 3.2 ER 图

```mermaid
erDiagram
    ANALYSES {
        int id PK
        string code_hash "索引"
        string language
        int code_length
        text roast_text
        int chaos_score
        text suggestions
        string status
        datetime created_at
    }
    COMMITS {
        int id PK
        string repo
        string commit_sha "索引"
        int total_additions
        int total_deletions
        int analysis_id FK
        datetime created_at
    }
    MEMES {
        int id PK
        int analysis_id FK
        string png_path
        datetime created_at
    }

    ANALYSES ||--o{ COMMITS : "1 对多"
    ANALYSES ||--o{ MEMES : "1 对多"
```

---

## 行为模型

### 4.1 系统时序图

以下是一次完整「代码评审」调用链（前端 → 后端 → LLM → 数据库）。

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant FE as React 前端
    participant BE as FastAPI 后端
    participant LLM as LLM API
    participant DB as SQLite 数据库

    U->>FE: 输入代码并点击「开始评审」
    FE->>BE: POST /roast {code, language}
    BE->>BE: 参数校验（Pydantic）
    BE->>LLM: 发送 prompt（system + code）
    alt LLM 已配置
        LLM-->>BE: {roast_text, chaos_score, suggestions}
    else 未配置（回退）
        BE-->>BE: 本地确定性生成器
    end
    BE->>DB: INSERT INTO analyses
    DB-->>BE: 返回记录 id
    BE-->>FE: 200 {id, roast_text, chaos_score, suggestions}
    FE-->>U: 展示评审结果
```

### 4.2 状态机图

分析任务的生命周期（`pending → processing → success / failed`）。

```mermaid
stateDiagram-v2
    [*] --> pending : 请求进入队列
    pending --> processing : 开始调用 LLM
    processing --> success : LLM 返回合法结果并落库
    processing --> failed : LLM 调用异常 / 结果非法
    success --> [*] : 记录持久化完成
    failed --> [*] : 回退或返回错误
```

---

## 技术架构与关键决策

| 决策点 | 方案 | 理由 |
| --- | --- | --- |
| LLM 接入 | `openai` 库 + `base_url` 兼容端点 | 一套代码适配硅基流动 / Azure / DeepSeek |
| 未配置密钥 | 本地确定性回退生成器 | 保证测试、演示、CI 无需外部依赖即可运行 |
| GitHub 拉取 | `httpx` + `Accept: diff` 头 | 直接拿到 unified diff，免拼接 |
| 梗图生成 | **Pillow 模板化方案（方案 A）** | 无需图像生成 AI，成本低、速度快、结果确定 |
| 数据库 | SQLite（开发）+ SQLAlchemy ORM | 可无缝切换 PostgreSQL |
| 测试 | pytest + pytest-bdd | 单测 + BDD，覆盖率目标 ≥ 70% |
| 限流 | 内置轻量方案（可扩展 slowapi） | 防御性编程，防滥用 |

---

## 非功能需求

- **性能**：单次评审响应 < 10s（含 LLM 调用）；梗图生成 < 2s。
- **可观测性**：结构化日志（`logging`），关键链路含时间戳与模块名。
- **安全**：Webhook 使用 HMAC-SHA256 签名校验；GitHub Token 仅存环境变量。
- **可移植性**：Docker 一键启动；配置全环境变量化。
- **可测试性**：核心服务与 LLM/GitHub 解耦，可注入 mock。
