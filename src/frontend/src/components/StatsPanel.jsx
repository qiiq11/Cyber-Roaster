import React, { useEffect, useState } from 'react'
import { api } from '../api/client.js'

/**
 * 统计面板：展示评审总数、平均混乱度、提交数与梗图数。
 */
export default function StatsPanel() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!stats) return <p>加载中……</p>

  const items = [
    { label: '评审总数', value: stats.total_analyses },
    { label: '平均混乱度', value: stats.average_chaos_score },
    { label: '最高混乱度', value: stats.max_chaos_score },
    { label: '最低混乱度', value: stats.min_chaos_score },
    { label: '分析提交数', value: stats.total_commits },
    { label: '生成梗图数', value: stats.total_memes },
  ]

  return (
    <div className="stats-grid">
      {items.map((it) => (
        <div className="stat-card" key={it.label}>
          <span className="stat-value">{it.value}</span>
          <span className="stat-label">{it.label}</span>
        </div>
      ))}
    </div>
  )
}
