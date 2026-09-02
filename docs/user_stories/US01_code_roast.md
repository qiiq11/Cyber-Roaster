# US01 · 代码幽默评审

## 元信息

| 字段 | 内容 |
| --- | --- |
| 故事 ID | US01 |
| 标题 | 代码幽默评审 |
| 优先级 | P0（核心） |
| 所属 Sprint | Sprint 1 |
| 相关接口 | `POST /roast`、`GET /roast/{id}` |

## 故事描述

> **As a** 开发者
> **I want** 提交一段代码并获得幽默而善意的评审
> **So that** 我能在轻松的氛围里发现代码中值得改进的地方。

## 验收标准（Acceptance Criteria）

- [ ] 提交合法代码后，接口返回 `roast_text`、`chaos_score`（0–100）、`suggestions`（至少 1 条）。
- [ ] 每次评审被持久化到 `analyses` 表，含时间戳与代码长度。
- [ ] 空代码或缺失字段返回 422 校验错误。
- [ ] 可通过 `GET /roast/{id}` 查询历史评审。
- [ ] 未配置 LLM 密钥时，系统仍能返回确定性回退评审（保证演示可用）。

## Gherkin 场景

```gherkin
功能: 代码幽默评审
  作为一个开发者
  我想提交代码片段并得到幽默评审
  以便在笑声中获得改进建议

  场景: 提交合法代码获得评审
    假如 我提交了一段合法的 Python 代码
    当 我调用评审接口
    那么 接口返回 200 状态码
    并且 响应包含 roast_text 字段
    并且 响应包含 chaos_score 字段
    并且 chaos_score 在 0 到 100 之间

  场景: 提交空代码被拒绝
    假如 我提交一段空代码
    当 我调用评审接口
    那么 接口返回 422 状态码

  场景: 查询不存在的评审记录
    假如 我请求一个不存在的评审 id
    当 我调用评审查询接口
    那么 接口返回 404 状态码

  场景: 统计接口反映评审数量
    假如 我提交了一段合法的 Python 代码
    当 我调用评审接口
    并且 我调用统计接口
    那么 统计接口返回 total_analyses 为 1
```

## 故事级架构图

### 1. 故事上下文与边界图

```mermaid
flowchart TD
    subgraph 边界["US01 代码幽默评审"]
        FE[RoastForm 组件]
        API["POST /roast"]
        SVC[RoastService]
        LLM[LLMClient]
        DB[(analyses 表)]
    end

    User((开发者)) -->|代码 + 语言| FE
    FE -->|HTTP| API
    API --> SVC
    SVC --> LLM
    LLM -->|评审结果| SVC
    SVC --> DB
    DB -->|记录 id| API
    API -->|RoastResponse| FE
```

### 2. 组件 / 数据流图

```mermaid
flowchart LR
    A[代码片段] --> B[Pydantic 校验<br/>RoastRequest]
    B --> C[RoastService.roast]
    C --> D{LLM 已配置?}
    D -- 是 --> E[OpenAI 兼容 API]
    D -- 否 --> F[本地回退生成器]
    E --> G[解析 JSON]
    F --> G
    G --> H[AnalysisRecord 持久化]
    H --> I[RoastResponse 返回]
```

### 3. 领域类与数据契约图

```mermaid
classDiagram
    class RoastRequest {
        +str code
        +str language
    }
    class RoastResponse {
        +int id
        +str roast_text
        +int chaos_score
        +list suggestions
        +str language
        +int code_length
        +datetime created_at
    }
    class RoastService {
        +roast(RoastRequest) RoastResponse
        +get(int) AnalysisRecord
    }
    class LLMClient {
        +generate_roast(str, str) dict
    }
    RoastService --> RoastRequest : 消费
    RoastService --> RoastResponse : 产出
    RoastService --> LLMClient : 依赖
```

### 4. 数据实体 / 持久化模型图

```mermaid
erDiagram
    ANALYSES {
        int id PK
        string code_hash
        string language
        int code_length
        text roast_text
        int chaos_score
        text suggestions
        string status
        datetime created_at
    }
```

### 5. 端到端时序交互图

```mermaid
sequenceDiagram
    actor U as 开发者
    participant FE as RoastForm
    participant BE as /roast
    participant SVC as RoastService
    participant LLM as LLMClient
    participant DB as analyses

    U->>FE: 填写代码并提交
    FE->>BE: POST /roast {code, language}
    BE->>BE: RoastRequest 校验
    BE->>SVC: roast(request)
    SVC->>LLM: generate_roast(code, language)
    LLM-->>SVC: {roast_text, chaos_score, suggestions}
    SVC->>DB: add + commit
    DB-->>SVC: record(id)
    SVC-->>BE: AnalysisRecord
    BE-->>FE: 200 RoastResponse
    FE-->>U: 展示评审
```

### 6. 状态机与活动流程图

```mermaid
stateDiagram-v2
    [*] --> 校验中
    校验中 --> 校验失败 : 空代码/缺字段
    校验中 --> LLM调用中 : 校验通过
    LLM调用中 --> 解析中 : 返回结果
    LLM调用中 --> 回退 : 调用异常
    回退 --> 解析中
    解析中 --> 落库成功 : 解析合法
    解析中 --> 回退 : 解析失败
    落库成功 --> [*]
    校验失败 --> [*]
```
