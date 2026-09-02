import React from 'react'
import { api } from '../api/client.js'

/**
 * 评审结果展示：评语、混乱度进度条与改进建议，附“生成梗图”按钮。
 */
export default function ResultDisplay({ result, onMeme }) {
  const score = result.chaos_score ?? 0

  async function handleGenerateMeme() {
    try {
      const meme = await api.generateMeme(result.id)
      onMeme(meme)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="result-display">
      <div className="roast-text">{result.roast_text}</div>

      <div className="score-row">
        <span>混乱度评分</span>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${score}%` }}
          />
        </div>
        <span className="score-value">{score} / 100</span>
      </div>

      {result.suggestions?.length > 0 && (
        <ul className="suggestions">
          {result.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}

      <button className="btn-secondary" onClick={handleGenerateMeme}>
        🖼️ 生成梗图
      </button>
    </div>
  )
}
