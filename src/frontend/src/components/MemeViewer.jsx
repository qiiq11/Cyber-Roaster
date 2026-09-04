import React from 'react'
import { api } from '../api/client.js'

/**
 * 梗图查看器：预览生成的 PNG 并提供下载。
 */
export default function MemeViewer({ meme }) {
  const src = api.memeUrl(meme.id)
  return (
    <div className="meme-viewer">
      <h3>赛博表情包</h3>
      <img src={src} alt="代码评审梗图" className="meme-img" />
      <a className="btn-secondary" href={src} download="roast.png">
        ⬇️ 下载 PNG
      </a>
    </div>
  )
}
