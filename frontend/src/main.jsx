import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import SentinelCoreDashboard from './SentinelCoreDashboard.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SentinelCoreDashboard />
  </StrictMode>,
)
