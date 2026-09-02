# US03 · 梗图生成器

## 元信息

| 字段 | 内容 |
| --- | --- |
| 故事 ID | US03 |
| 标题 | 梗图生成器 |
| 优先级 | P1（高） |
| 所属 Sprint | Sprint 4 |
| 相关接口 | `POST /meme/{analysis_id}`、`GET /meme/{meme_id}` |

## 故事描述

> **As a** 开发者
> **I want** 把评审结果一键生成四格漫画并下载 PNG
> **So that** 我能在社交媒体上分享这段「代码吐槽」，娱乐团队。

## 验收标准（Acceptance Criteria）

- [ ] 对已存在的评审记录，可调用 `/meme/{analysis_id}` 生成 PNG。
- [ ] 漫画为四格：案情陈述、评审毒舌、混乱度评分、改进建议。
- [ ] 评分格包含可视化评分进度条。
- [ ] 生成的 PNG 可通过 `GET /meme/{meme_id}` 下载。
- [ ] 对不存在的评审 id 返回 404。
- [ ] 使用 Pillow 模板化方案，不依赖图像生成 AI。

## Gherkin 场景

```gherkin
功能: 梗图生成
  作为一个开发者
  我想把评审结果生成四格漫画
  以便分享代码吐槽

  场景: 为已存在评审生成梗图
    假如 存在一条评审记录
    当 我调用梗图生成接口
    那么 接口返回 200 状态码
    并且 响应包含 png_url 字段

  场景: 为不存在评审生成梗图
    假如 不存在该评审记录
    当 我调用梗图生成接口
    那么 接口返回 404 状态码

  场景: 下载生成的梗图
    假如 已生成一条梗图记录
    当 我调用梗图下载接口
    那么 接口返回 PNG 图片
    并且 内容类型为 image/png
```

## 故事级架构图

### 1. 故事上下文与边界图

```mermaid
flowchart TD
    subgraph 边界["US03 梗图生成"]
        FE[MemeViewer 组件]
        API["POST /meme/{analysis_id}"]
        DL["GET /meme/{meme_id}"]
        MG[MemeGenerator]
        DB[(memes 表)]
        FS[(static/memes 目录)]
    end

    User((开发者)) -->|点击生成| FE
    FE --> API
    API --> MG
    MG -->|PNG 字节流| FS
    API --> DB
    FE --> DL
    DL --> FS
```

### 2. 组件 / 数据流图

```mermaid
flowchart LR
    A[AnalysisRecord] --> B[analysis_to_dict]
    B --> C[generate_meme_png]
    C --> D[四格画布绘制<br/>Pillow]
    D --> E[保存 PNG 到 static/memes]
    E --> F[写入 memes 表]
    F --> G[返回 png_url]
```

### 3. 领域类与数据契约图

```mermaid
classDiagram
    class MemeResponse {
        +int id
        +int analysis_id
        +str png_url
    }
    class MemeGenerator {
        +generate_meme_png(dict) bytes
    }
    class AnalysisRecord {
        +str roast_text
        +int chaos_score
        +list suggestions
    }
    MemeGenerator --> AnalysisRecord : 读取
    MemeGenerator --> MemeResponse : 产出
```

### 4. 数据实体 / 持久化模型图

```mermaid
erDiagram
    ANALYSES {
        int id PK
        text roast_text
        int chaos_score
    }
    MEMES {
        int id PK
        int analysis_id FK
        string png_path
    }
    ANALYSES ||--o{ MEMES : "1 对多"
```

### 5. 端到端时序交互图

```mermaid
sequenceDiagram
    actor U as 开发者
    participant FE as ResultDisplay
    participant BE as /meme/{id}
    participant MG as MemeGenerator
    participant FS as static/memes
    participant DB as memes 表

    U->>FE: 点击「生成梗图」
    FE->>BE: POST /meme/{analysis_id}
    BE->>DB: 查询 AnalysisRecord
    DB-->>BE: record
    BE->>MG: generate_meme_png(analysis)
    MG-->>BE: PNG bytes
    BE->>FS: 写入 meme_xxx.png
    BE->>DB: INSERT memes
    DB-->>BE: meme(id)
    BE-->>FE: {id, analysis_id, png_url}
    FE->>BE: GET /meme/{meme_id}
    BE-->>FE: PNG 文件
    FE-->>U: 预览 + 下载
```

### 6. 状态机与活动流程图

```mermaid
stateDiagram-v2
    [*] --> 查询评审
    查询评审 --> 不存在 : id 无效
    查询评审 --> 绘制漫画 : 找到记录
    绘制漫画 --> 保存PNG
    保存PNG --> 写入记录
    写入记录 --> 返回地址
    返回地址 --> [*]
    不存在 --> [*]
```
