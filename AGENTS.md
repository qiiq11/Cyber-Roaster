# AGENTS.md — AI 助手规则注入

本文件为在此仓库中工作的 AI 助手（如 Claude Code）提供强制约束。

## 通用规则

1. **语言**：所有输出、代码注释、文档一律使用简体中文。
2. **提交规范**：commit message 遵循 Angular 规范
   （`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`）。
3. **图表**：所有文档图表使用 Mermaid 语法。

## 代码规范

- 后端遵循 PEP 8，使用 `black`（行宽 88）与 `flake8` 校验。
- 前端使用函数式组件 + Hooks，样式集中在 `cyberpunk.css`。
- 新增接口必须在 `tests/` 下补充单元测试。

## 关键技术决策

- LLM 通过 OpenAI 兼容 API 接入（`openai` 库 + `base_url`）。
- 未配置 LLM 密钥时使用本地确定性回退生成器。
- 梗图生成采用 **Pillow 模板化方案**（不调用图像生成 AI）。
- 数据库开发用 SQLite，生产可切换 PostgreSQL。

## 安全约束

- 任何密钥/Token 只能通过环境变量注入，禁止硬编码。
- Webhook 必须校验 HMAC-SHA256 签名。
