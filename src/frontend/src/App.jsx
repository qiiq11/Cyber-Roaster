import React, { useState } from 'react'
import RoastForm from './components/RoastForm.jsx'
import ResultDisplay from './components/ResultDisplay.jsx'
import StatsPanel from './components/StatsPanel.jsx'
import GitHubAnalyzer from './components/GitHubAnalyzer.jsx'
import MemeViewer from './components/MemeViewer.jsx'

/**
 * 应用根组件：组合评审、统计、GitHub 分析与梗图四大模块。
 */
export default function App() {
  const [result, setResult] = useState(null)
  const [meme, setMeme] = useState(null)

  return (
    <div className="app">
      <header className="app-header">
        <h1>⚡ CYBER-ROASTER ⚡</h1>
        <p className="tagline">AI 幽默代码评审 & 梗图生成器</p>
      </header>

      <main className="app-main">
        <section className="panel">
          <h2>提交代码评审</h2>
          <RoastForm onResult={setResult} />
        </section>

        {result && (
          <section className="panel">
            <h2>评审结果</h2>
            <ResultDisplay result={result} onMeme={setMeme} />
            {meme && <MemeViewer meme={meme} />}
          </section>
        )}

        <section className="panel">
          <h2>统计面板</h2>
          <StatsPanel />
        </section>

        <section className="panel">
          <h2>GitHub 提交分析</h2>
          <GitHubAnalyzer onResult={setResult} />
        </section>
      </main>
    </div>
  )
}
