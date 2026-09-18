# Cyber-Roaster 项目实验报告

> 基于 AI 的幽默代码评审与梗图生成工具 · 工程化全流程交付总结

---

## 1. 开发环境及相关技术

### 1.1 操作系统与运行时

| 项目 | 版本 |
| --- | --- |
| 操作系统 | Windows 11 Home China（10.0.26200） |
| Python | 3.12.6 |
| Node.js | v24.14.0 |
| 包管理 | pip / npm |

### 1.2 后端技术栈（提取自 `src/backend/requirements.txt`）

| 库 | 版本 | 用途 |
| --- | --- | --- |
| FastAPI | 0.111.0 | 后端 Web 框架 |
| uvicorn | 0.30.1 | ASGI 服务器 |
| pydantic | 2.7.4 | 数据校验与序列化 |
| pydantic-settings | 2.3.4 | 环境变量配置加载 |
| SQLAlchemy | 2.0.31 | ORM 数据库操作 |
| httpx | 0.27.0 | GitHub API / memegen.link 调用 |
| openai | 1.35.7 | OpenAI 兼容 LLM 接入 |
| Pillow | 10.3.0 | 梗图降级方案（自绘漫画） |
| javalang | 0.13.0 | Java 代码 AST 解析 |
| pytest | 8.2.2 | 单元测试框架 |
| pytest-bdd | 7.2.0 | BDD 行为测试 |
| black / flake8 | 24.4.2 / 7.1.0 | 代码格式化与规范检查 |

### 1.3 前端技术栈（提取自 `src/frontend/package.json`）

| 库 | 版本 | 用途 |
| --- | --- | --- |
| React | 18.3.1 | 前端 UI 框架 |
| Vite | 5.3.3 | 构建工具与开发服务器 |
| @vitejs/plugin-react | 4.3.1 | Vite 的 React 插件 |

### 1.4 AI 服务

后端通过 OpenAI 兼容 API 接入大模型，支持硅基流动（SiliconFlow）与 DeepSeek 两个服务商，通过 `OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_API_KEY` 三个环境变量配置。默认模型为 `deepseek-ai/DeepSeek-V3`，实际部署时可根据需要在 `.env` 中切换。

---

## 2. 代码规范要求

### 2.1 CI 自动化检查（`.github/workflows/ci.yml`）

项目配置了 GitHub Actions 流水线，包含两个 Job：

- **lint-test**（代码检查与测试）：
  - `black --check app tests`：检查代码是否符合 Black 格式（行宽 88）。
  - `flake8 app tests --max-line-length=100 --extend-ignore=E203,W503`：检查代码规范（忽略 E203/W503 与 Black 的冲突项）。
  - `pytest`：运行测试并检查覆盖率（目标 ≥70%，由 `pytest.ini` 中的 `--cov-fail-under=70` 强制）。
- **build-images**（构建镜像）：依赖 `lint-test` 通过后，分别构建后端与前端 Docker 镜像。

### 2.2 AI 规则注入规范（`AGENTS.md` / `.rules`）

- 所有输出、代码注释、文档一律使用简体中文。
- 提交信息遵循 Angular 规范（`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:` / `style:`）。
- 文档图表统一使用 Mermaid 语法。
- 后端遵循 PEP 8，使用 black（行宽 88）与 flake8 校验。
- 任何密钥/Token 只能通过环境变量注入，禁止硬编码。

### 2.3 Angular 语义化提交规范

项目全程遵循 Angular 规范提交，实际提交历史示例：

```
feat: 完成 Cyber-Roaster 核心功能修复与增强
docs: 更新 README 功能描述与环境变量说明
style: 运行 black 格式化后端代码
fix(backend): 修复 Java POJO 类评分偏差与嵌套深度计算
```

---

## 3. 设计和实现过程

### 3.1 需求分析

#### 核心用户故事

从 `docs/user_stories/` 提取三个核心用户故事：

| 故事 | 描述 | 关键验收标准 |
| --- | --- | --- |
| US01 代码幽默评审 | 作为开发者，我想提交代码并获得幽默评审 | 返回 `roast_text`、`chaos_score`（0–100）、`suggestions`；空代码返回 422；可查询历史评审 |
| US02 GitHub 提交分析 | 作为团队成员，我想输入仓库+Commit 自动分析 Diff | 解析修改文件与增删行数；Webhook 校验 HMAC 签名；未配置 Token 返回模拟数据 |
| US03 梗图生成 | 作为开发者，我想一键生成梗图并下载 | 对已存在评审生成 PNG；评分格可视化；支持下载 |

#### 用例图描述（提取自 `docs/system_design.md`）

系统边界内包含五个核心用例：提交代码评审（`/roast`）、查看统计（`/stats`）、分析 GitHub 提交（`/github/analyze`）、生成梗图（`/meme`）、接收 Webhook 自动评审（`/webhook/github`）。参与者包括用户、LLM API、GitHub Webhook 三个外部实体。

#### 核心功能需求总结

1. **AI 代码评审**：提交代码片段，调用 LLM 生成幽默评语、混乱度评分与改进建议。
2. **统计面板**：展示评审总数、平均/最高/最低混乱度等聚合数据。
3. **GitHub 集成**：拉取提交 Diff 分析，Webhook 自动触发评审。
4. **梗图生成**：基于评审结果生成梗图 PNG 并支持下载。

### 3.2 数据库设计

从 `src/backend/app/models/database.py` 提取 ORM 模型，共三张表：

**analyses 表**（评审记录，核心实体）：

```python
class AnalysisRecord(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code_hash = Column(String(64), index=True, nullable=False)
    language = Column(String(32), nullable=False, default="python")
    code_length = Column(Integer, nullable=False)
    roast_text = Column(Text, nullable=False)
    chaos_score = Column(Integer, nullable=False)
    suggestions = Column(Text, nullable=False)  # JSON 数组序列化后的字符串
    status = Column(String(16), nullable=False, default="success")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
```

**commits 表**（GitHub 提交记录，关联评审）：

```python
class Commit(Base):
    __tablename__ = "commits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(200), nullable=False)
    commit_sha = Column(String(64), index=True, nullable=False)
    total_additions = Column(Integer, nullable=False, default=0)
    total_deletions = Column(Integer, nullable=False, default=0)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
```

**memes 表**（梗图记录，关联评审）：

```python
class Meme(Base):
    __tablename__ = "memes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    png_path = Column(String(500), nullable=False)
```

**表关系**：`analyses` 与 `commits`、`memes` 均为「1 对多」关系，通过 `analysis_id` 外键关联。

**数据库选型**：开发环境使用 SQLite（`DATABASE_URL` 默认 `sqlite:///./cyber_roaster.db`），通过 SQLAlchemy ORM 解耦，仅需修改 `DATABASE_URL` 即可无缝切换 PostgreSQL。此外，代码对内存 SQLite 特殊处理，使用 `StaticPool` 让所有连接共享同一份内存数据库，保证测试隔离正确。

### 3.3 功能实现

#### （1）代码评审模块

核心流程位于 `app/api/roast.py` 与 `app/services/roast_service.py`。在调用 LLM 之前，先用 AST 静态解析代码，提取「代码事实锚点」以对抗 AI 幻觉：

```python
async def roast(self, request: RoastRequest) -> AnalysisRecord:
    # 在调用 LLM 之前，先用 AST 提取真实的代码结构事实
    structure = analyze_code_structure(request.code, request.language)
    result = await self.llm.generate_roast(
        request.code,
        request.language,
        max_nesting_depth=structure["max_nesting_depth"],
        variables=structure["variables"],
    )
```

**AST 反幻觉锚点**由两部分构成：

- **变量名提取**（`VariableCollector`）：通过判断 `ast.Name.ctx` 是否为 `ast.Store`，只捕获「赋值目标」变量，排除类型注解（如 `List[float]` 中的 `List`）与 Python 关键字。
- **嵌套深度评分**：递归遍历 AST 计算真实最大嵌套深度，注入 Prompt 作为硬性评分锚点——嵌套深度 ≤2 时，`chaos_score` 必须 ≤20，防止 AI 对简单代码给出虚高评分。

**多语言支持**：`analyze_code_structure()` 按 `language` 参数分流：

```python
if lang in ("python", "py"):
    return _analyze_python(code)          # ast 精确解析
if lang == "java":
    return _analyze_java(code)            # javalang 解析
return _regex_extract_variables(code, lang)  # 正则回退
```

- Python：使用 `ast` 模块精确解析。
- Java：使用 `javalang` 提取类名、方法名、参数名、字段名，并计算嵌套深度。
- 其他语言：正则回退提取顶层函数/类名，解析失败时返回占位符 `["（无法识别变量名）"]`，避免空列表导致 AI 编造变量名。

#### （2）统计模块

`app/services/stats_service.py` 使用 SQLAlchemy 聚合查询：

```python
def get_summary(self) -> Dict[str, Any]:
    total = self.db.query(func.count(AnalysisRecord.id)).scalar() or 0
    avg = (
        self.db.query(func.avg(AnalysisRecord.chaos_score)).scalar()
        if total > 0
        else 0.0
    )
    max_score = self.db.query(func.max(AnalysisRecord.chaos_score)).scalar() or 0
    # ... 返回 total_analyses、average_chaos_score、max/min、commits、memes 等
```

#### （3）GitHub 集成

`app/api/github.py` + `app/core/github_client.py`：

- 通过 `httpx` + `Accept: application/vnd.github.v3.diff` 头拉取 unified diff。
- 解析 `diff --git`、`+`、`-` 前缀，统计每个文件的增删行数。
- **超长 diff 截断**：真实提交的 diff 可能达数百 KB，远超 `RoastRequest.code` 的 20000 上限，因此截断到 18000 字符用于 LLM 评审（文件统计仍基于完整 diff），并兜底捕获 `ValidationError` 避免 500：

```python
_MAX_DIFF_CHARS = 18000
diff_text = diff["diff_text"][:_MAX_DIFF_CHARS]
try:
    roast_payload = RoastRequest(code=diff_text, language="diff")
    record = await service.roast(roast_payload)
except ValidationError as exc:
    raise HTTPException(status_code=422, detail=f"Diff 内容无效：{exc}") from exc
```

- Webhook 端点校验 HMAC-SHA256 签名，处理 Push 事件自动触发评审。

#### （4）梗图生成

`app/api/meme.py` + `app/core/meme_generator.py`：

- **主方案**：调用免费 memegen.link API，随机选取模板（drake、buzz、disastergirl、spongebob、yuno），将 `roast_text` 作为上排文字、`chaos_score` 作为下排文字填入。
- **降级方案**：memegen.link 请求失败时，自动降级回 Pillow 自绘四格漫画，保证功能不中断：

```python
def generate_meme_png(analysis: Dict[str, Any]) -> bytes:
    if settings.meme_template_preference.lower() == "memegen":
        template = random.choice(MEME_TEMPLATES)
        png = _fetch_memegen(template, top_text, bottom_text)
        if png is not None:
            return png
        logger.warning("memegen.link 不可用，降级到 Pillow 自绘方案")
    return _generate_meme_png_pillow(analysis)
```

### 3.4 系统运行结果

#### 前端界面

前端包含五个核心页面/组件：

- **RoastForm**：代码输入框 + 语言选择，提交评审。
- **ResultDisplay**：展示评语、混乱度进度条（三段渐变）、改进建议列表，附「生成梗图」按钮。
- **StatsPanel**：卡片式统计面板，展示评审总数、平均混乱度等 6 项指标。
- **GitHubAnalyzer**：输入仓库名 + Commit SHA，分析提交。
- **MemeViewer**：预览生成的「赛博表情包」并下载 PNG。

[待补充：前端主界面截图「见图 1」]

[待补充：评审结果与梗图展示截图「见图 2」]

#### API 文档

后端启动后访问 `http://localhost:8000/docs`，FastAPI 自动生成交互式 Swagger 文档，可在线测试全部 8 个接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/roast` | 提交代码评审 |
| GET | `/roast/{id}` | 查询评审记录 |
| GET | `/stats` | 统计概览 |
| POST | `/github/analyze` | 分析 GitHub 提交 |
| POST | `/webhook/github` | 接收 Push 事件 |
| POST | `/meme/{analysis_id}` | 生成梗图 |
| GET | `/meme/{meme_id}` | 下载梗图 PNG |
| GET | `/health` | 健康检查 |

[待补充：Swagger 文档截图「见图 3」]

### 3.5 测试

#### 测试结果

```text
19 passed, 1 warning
Total coverage: 82.96%
```

- **单元测试**：16 个（位于 `tests/unit/test_roast.py`）。
- **BDD 测试**：3 个场景（位于 `tests/bdd/features/roast.feature`）。

#### 测试策略

采用「单元测试 + BDD 行为测试」双层策略：

- **单元测试**（pytest）：覆盖核心接口的请求/响应、状态码、字段校验，以及 `analyze_code_structure` 的多语言变量提取逻辑。
- **BDD 测试**（pytest-bdd）：用 Gherkin 语法描述业务场景，例如：

```gherkin
Scenario: 提交合法代码获得评审
  Given 我提交了一段合法的 Python 代码
  When 我调用评审接口
  Then 接口返回 200 状态码
  And 响应包含 roast_text 字段
  And chaos_score 在 0 到 100 之间
```

#### 关键测试场景

1. 代码评审接口的基本校验（合法代码 / 空代码 / 缺失字段）。
2. 变量提取：Java POJO 类不把 `diff`、`List`、`Dict` 等误认为变量。
3. 多语言支持：Python（ast）、Java（javalang）、JS/C++（正则回退）、无法解析时返回占位符。
4. 梗图生成与 PNG 下载。
5. Webhook ping 事件处理。

测试隔离通过 `conftest.py` 实现：强制内存 SQLite、空值覆盖环境变量（避免 `.env` 文件干扰），保证测试不依赖外部网络与真实密钥。

[待补充：pytest 测试结果截图「见图 4」]

---

## 4. 总结体会

### 4.1 项目过程回顾

本项目从最初的一个想法——「用 AI 给代码来点幽默吐槽」——逐步演进为一个完整的全栈工程化产品。整个开发过程经历了清晰的迭代：先是搭建 FastAPI + React 的 MVP 骨架，打通「提交代码 → LLM 评审 → 落库 → 前端展示」的最小闭环；随后补充统计面板、GitHub 集成、梗图生成；最后是持续的反幻觉优化、多语言支持、CI 格式修复与文档完善。每一步都伴随着测试的同步补齐，最终达成了 82.96% 的测试覆盖率与完整的工程化交付。

### 4.2 技术收获

这次开发让我系统性地实践了多个技术栈的组合：FastAPI 的依赖注入与自动文档、SQLAlchemy 的 ORM 建模与内存库隔离、React Hooks 的函数式组件、OpenAI 兼容 API 的接入与 Prompt 工程、Python AST 与 javalang 的静态代码解析、GitHub REST API 与 Webhook 的鉴权集成。其中最有价值的是对 **AST 解析**的深入理解——从最初简单地 `ast.walk` 收集所有名称，到后来精确区分 `Store`/`Load` 上下文、过滤类型注解、计算嵌套深度，这个过程让我真正理解了静态分析在对抗 LLM 幻觉中的实际价值。

### 4.3 遇到的挑战

1. **AI 幻觉问题**是最棘手的挑战。LLM 会凭空编造变量名（把 `from`、`diff`、`List` 当变量）、给出虚高评分（对简单 POJO 打 95 分）。解决方案是引入「代码事实锚点」——用 AST 提取真实变量与嵌套深度，注入 Prompt 并设置硬性评分约束，同时让本地回退生成器也遵守同样的锚点逻辑。
2. **Java 支持**：`ast` 只能解析 Python，需要引入 `javalang` 并理解其 `path` 遍历机制，正确计算嵌套深度（关键教训是深度要对所有节点计算，而非仅嵌套语句节点）。
3. **CI 格式检查**：Black 与 Flake8 的冲突项（E203/W503）、未使用导入、超长行等细节问题，需要反复调整。
4. **测试隔离**：`.env` 文件的配置会干扰测试（`os.environ.pop` 无法覆盖 `.env`），需改为空值覆盖；内存 SQLite 需要 `StaticPool` 才能让建表对后续连接可见。

### 4.4 对 AI 辅助开发的感受

这次项目全程使用 Claude Code 辅助开发，让我深刻体会到 AI 辅助开发的「放大器」效应。AI 能极快地生成项目骨架、编写模板代码、补齐测试，大大提升了初始搭建的效率。但同样重要的是，**AI 不是万能的**：它会犯下真实但隐蔽的错误——例如最初把 `docs_url` 显式声明当作「修复」，其实默认值本就正确；也会在多轮迭代中产生需要仔细验证的边界问题（如 Java 嵌套深度少算一层）。这让我意识到，AI 辅助开发的关键在于**人机协作的质量**：人类需要清晰地表达需求、审慎地验证 AI 的输出、并理解 AI 每一步改动的真实影响，而不能盲目信任。

### 4.5 未来改进方向

1. **多语言 AST 扩展**：目前 Java 之外的 C++、Go、Rust 仍依赖正则回退，可引入 tree-sitter 等通用解析器实现真正的多语言 AST 分析。
2. **真正的四格漫画**：当前主方案是单张梗图，降级方案才画四格漫画，可探索将四格叙事与 LLM 生成内容更深度结合。
3. **部署上线**：接入真实数据库（PostgreSQL）、配置 CI/CD 自动部署、增加用户系统与梗图分享功能。
4. **流式输出**：评审结果采用 SSE 流式返回，提升用户体验。
5. **评分锚点精细化**：将「嵌套深度 ≤2 → ≤20」的硬阈值扩展为更细粒度的复杂度分级模型。

---

*报告完成于 2026 年 9 月，基于 Cyber-Roaster 项目实际代码与文档生成。*
