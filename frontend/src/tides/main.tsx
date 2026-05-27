import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/glacier.css'
import './styles/tides.css'
import './styles/tweaks.css'
import './styles/mobile.css'
import App from './App.tsx'

const root = document.getElementById('tides-root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
