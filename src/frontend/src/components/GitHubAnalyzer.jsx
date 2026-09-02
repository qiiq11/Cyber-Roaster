import React, { useState } from 'react'
import { api } from '../api/client.js'

/**
 * GitHub 提交分析表单：输入仓库与 Commit SHA，拉取 Diff 并评审。
 */
export default function GitHubAnalyzer({ onResult }) {
  const [repo, setRepo] = useState('')
  const [commitSha, setCommitSha] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!repo.trim() || !commitSha.trim()) {
      setError('仓库名与 Commit SHA 均不能为空')
      return
    }
    setLoading(true)
    try {
      const data = await api.analyzeGithub(repo.trim(), commitSha.trim())
      onResult(data.roast)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="github-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>仓库全名（owner/name）</span>
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="octocat/hello-world"
        />
      </label>
      <label className="field">
        <span>Commit SHA</span>
        <input
          value={commitSha}
          onChange={(e) => setCommitSha(e.target.value)}
          placeholder="abc123def456"
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? '分析中……' : '🔍 分析提交'}
      </button>
    </form>
  )
}
