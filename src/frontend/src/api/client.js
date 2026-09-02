// 后端 API 客户端封装
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

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
