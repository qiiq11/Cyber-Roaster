# ⚡ Cyber-Roaster · AI 幽默代码评审 & 梗图生成器

[![CI](https://github.com/your-org/cyber-roaster/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/cyber-roaster/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

把代码提交给 AI，收获一份**毒舌但善意**的幽默评审，还能一键生成赛博朋克风格梗图——让 Code Review 从此不再枯燥。

## ✨ 功能特性

- 🧠 **AI 代码评审**：调用 OpenAI 兼容 LLM，返回评语、混乱度评分与改进建议。
- 📊 **统计面板**：评审总数、平均/最高/最低混乱度、提交数与梗图数。
- 🔗 **GitHub 集成**：输入仓库 + Commit SHA 自动拉取 Diff 分析；Webhook 实现「Push 即吐槽」。
- 🖼️ **梗图生成**：基于 memegen.link API 生成流行梗图，可预览并下载 PNG。
- 🐳 **一键启动**：Docker Compose 拉起前后端。
- 🧪 **完整测试**：pytest 单元测试 + pytest-bdd 行为测试，覆盖率 ≥ 70%。

## 🏗️ 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.10+ · FastAPI · SQLAlchemy · Pydantic |
| 前端 | React 18 · Vite |
| AI | OpenAI 兼容 API（硅基流动 / Azure / DeepSeek） |
| 数据库 | SQLite（开发）→ 可切换 PostgreSQL |
| 容器 | Docker + Docker Compose |
| CI | GitHub Actions（lint + test + build） |

## 📁 目录结构

```
cyber-roaster/
├── .github/              # CI 工作流、Issue/PR 模板
├── docs/                 # 系统设计、User Story、Sprint 报告
├── src/
│   ├── backend/          # FastAPI 后端
│   └── frontend/         # React + Vite 前端
├── docker-compose.yml
├── AGENTS.md             # AI 规则注入
├── .rules
└── README.md
```

## 🚀 快速启动

### 方式一：Docker 一键启动（推荐）

```bash
# 复制环境变量模板并按需填写
cp src/backend/.env.example .env

docker compose up --build
```

启动后：

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>

### 方式二：本地开发

**后端**

```bash
cd src/backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**前端**

```bash
cd src/frontend
npm install
npm run dev
```

## 🔑 环境变量说明

| 变量 | 必填 | 说明 | 默认值 |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | 是 | OpenAI 兼容 API 密钥 | 空 |
| `OPENAI_BASE_URL` | 否 | API 基础地址（硅基流动/Azure/DeepSeek） | `https://api.siliconflow.cn/v1` |
| `OPENAI_MODEL` | 否 | 模型名 | `deepseek-ai/DeepSeek-V3` |
| `GITHUB_TOKEN` | 按需 | GitHub 分析时需要 | 空 |
| `WEBHOOK_SECRET` | 否 | Webhook HMAC 密钥 | 空 |
| `DATABASE_URL` | 否 | 数据库连接串 | `sqlite:///./cyber_roaster.db` |
| `MEME_OUTPUT_DIR` | 否 | 梗图输出目录 | `./static/memes` |

> 说明：未配置 `OPENAI_API_KEY` 时后端会返回模拟评审数据（仅供演示），生产使用请务必配置。未配置 `GITHUB_TOKEN` 时 GitHub 分析会使用模拟 Diff，同样仅供演示。

## 📡 API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/roast` | 提交代码评审 |
| `GET` | `/roast/{id}` | 查询评审记录 |
| `GET` | `/stats` | 统计概览 |
| `POST` | `/github/analyze` | 分析 GitHub 提交 |
| `POST` | `/webhook/github` | 接收 Push 事件 |
| `POST` | `/meme/{analysis_id}` | 生成梗图 |
| `GET` | `/meme/{meme_id}` | 下载梗图 PNG |
| `GET` | `/health` | 健康检查 |

完整交互式文档见 <http://localhost:8000/docs>（FastAPI 自动生成）。

## 🧪 运行测试

```bash
cd src/backend
pytest                        # 单元 + BDD + 覆盖率
pytest tests/unit             # 仅单元测试
pytest tests/bdd              # 仅 BDD 场景
```

## 📦 打包为可执行文件

将项目打包为 Windows 可执行文件，双击即可启动，浏览器自动打开前端页面。

### 打包命令

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 构建前端产物
cd src/frontend
npm run build
cd ../..

# 3. 执行打包
pyinstaller build.spec --clean
```

### 产物位置

打包完成后，可执行文件位于：

```
dist/CyberRoaster.exe
```

### 使用方式

1. 将 `CyberRoaster.exe` 与 `.env` 文件放在同一目录（`.env` 由 `src/backend/.env.example` 复制并填写）。
2. 双击运行 `CyberRoaster.exe`。
3. 浏览器会自动打开 `http://127.0.0.1:8000`，即可使用全部功能。

### 注意事项

- 首次运行会在 exe 同级目录生成 `cyber_roaster.db` 和 `static/memes/` 目录，属正常行为。
- 未配置 `.env`（或未填写 `OPENAI_API_KEY`）时，后端走本地回退生成器，返回模拟评审数据（仅供演示）。
- 打包后的 exe 体积较大（约 95 MB，含 Python 运行时与全部依赖），属正常现象。
- 若杀毒软件误报，请选择「允许运行」。

## 📚 文档

- [系统设计（6 大架构图）](docs/system_design.md)
- [US01 代码评审](docs/user_stories/US01_code_roast.md)
- [US02 GitHub 分析](docs/user_stories/US02_github_analyzer.md)
- [US03 梗图生成](docs/user_stories/US03_meme_generator.md)
- [Sprint 1 报告](docs/sprint1_report.md) · [Sprint 2](docs/sprint2_report.md) · [Sprint 3](docs/sprint3_report.md) · [Sprint 4](docs/sprint4_report.md)

## 🎬 演示

> 演示视频链接占位：`https://example.com/demo`

## 📄 License

MIT
