# Cyber-Roaster 演示 PPT 截图清单

> 本清单对应 `docs/Cyber-Roaster-Demo.pptx` 的 8 页内容，标注每页需要补充的截图。

| 页码 | 页面标题 | 截图内容描述 | 建议截图来源 | 截图要点（需展示的元素） |
| --- | --- | --- | --- | --- |
| 1 | 封面 | 可选：项目 Logo 或标题装饰图 | 可自绘或使用项目图标 | 非必需，放 Logo 即可 |
| 2 | 项目简介 | 可选：产品概念图或整体海报 | 可自绘 | 非必需，体现「幽默点评代码」主题即可 |
| 3 | 核心功能 1：AI 代码评审 | 前端提交 Python 代码后的评审结果 | 前端页面 http://localhost:5173 | 毒舌评语（roast_text）、混乱度评分（chaos_score）、改进建议（suggestions）三要素 |
| 4 | 核心功能 2：GitHub 提交分析 | GitHub 分析页展示的文件变更统计 | 前端页面 http://localhost:5173（GitHub 分析栏） | 仓库名、Commit SHA、修改文件列表、增删行数、评审结果 |
| 5 | 核心功能 3：梗图生成 | 梗图生成后的预览画面 | 前端页面 http://localhost:5173（评审结果下方） | meme 图片、下载按钮（「赛博表情包」区域） |
| 6 | 统计面板 | 前端统计面板 | 前端页面 http://localhost:5173 | 评审总数、平均/最高/最低混乱度、提交数、梗图数六项指标 |
| 7 | 技术架构 | 后端 Swagger API 文档 | Swagger 文档 http://localhost:8000/docs | 8 个 API 接口列表（roast/stats/github/webhook/meme/health 等） |
| 8 | 总结与展望 | 可选：GitHub 仓库主页或 CI 通过截图 | GitHub 仓库页面 / GitHub Actions | 仓库主页或 CI 流水线绿色对勾 |

## 截图操作提示

1. **前端截图**：先启动后端（`uvicorn app.main:app --reload`），再启动前端（`npm run dev`），浏览器访问 http://localhost:5173。
2. **Swagger 截图**：后端启动后访问 http://localhost:8000/docs。
3. **Windows 截图快捷键**：`Win + Shift + S` 可区域截图。
4. 截图建议使用 PNG 格式，保持清晰。
