import React from 'react'
import { createRoot } from 'react-dom/client'

function App() {
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', margin: '4rem auto', maxWidth: 720, padding: '0 1rem' }}>
      <h1>Chanakya Research Commons</h1>
      <p>Local development foundation is running.</p>
      <p>API status: <a href="/api/health">check backend health</a></p>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
)
