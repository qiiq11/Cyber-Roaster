import React, { useState } from 'react'
import { api } from '../api/client.js'

/**
 * 代码评审表单：输入代码与语言，提交后回调结果。
 */
export default function RoastForm({ onResult }) {
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (!code.trim()) {
      setError('代码不能为空')
      return
    }
    setLoading(true)
    try {
      const result = await api.roast(code, language)
      onResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="roast-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>编程语言</span>
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="go">Go</option>
          <option value="rust">Rust</option>
          <option value="java">Java</option>
        </select>
      </label>
      <label className="field">
        <span>代码片段</span>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={8}
          placeholder="粘贴你的代码，接受毒舌评审……"
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? '评审中……' : '⚡ 开始评审'}
      </button>
    </form>
  )
}
