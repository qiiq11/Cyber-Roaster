// 后端 API 客户端封装
// API 地址动态判断：优先使用环境变量覆盖，其次根据运行环境推断。
// - 打包后由后端托管前端，两者同源，直接用 window.location.origin。
// - 开发环境（Vite dev server）经 proxy 转发到后端，同样用 origin。
// - 若以 file:// 协议打开（非常规场景），回退到固定地址。
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (window.location.origin.startsWith('file://')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

export default BASE_URL

/**
 * 通用 fetch 封装，自动拼接基础地址并解析 JSON。
 */
async function request(path, options = {}) {
  const resp = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const detail = await resp.text()
    throw new Error(`请求失败 (${resp.status}): ${detail}`)
  }
  return resp.json()
}

export const api = {
  // 代码评审
  roast(code, language = 'python') {
    return request('/roast', {
      method: 'POST',
      body: JSON.stringify({ code, language }),
    })
  },
  // 获取评审记录
  getRoast(id) {
    return request(`/roast/${id}`)
  },
  // 统计概览
  stats() {
    return request('/stats')
  },
  // GitHub 提交分析
  analyzeGithub(repo, commitSha) {
    return request('/github/analyze', {
      method: 'POST',
      body: JSON.stringify({ repo, commit_sha: commitSha }),
    })
  },
  // 生成梗图
  generateMeme(analysisId) {
    return request(`/meme/${analysisId}`, { method: 'POST' })
  },
  // 梗图 PNG 地址
  memeUrl(memeId) {
    return `${BASE_URL}/meme/${memeId}`
  },
  // 健康检查
  health() {
    return request('/health')
  },
}
