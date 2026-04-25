import { useState } from 'react'
import './App.css'

const NAV_ITEMS = [
  { label: 'Home',     href: '#', icon: '🏠' },
  { label: 'Leads',    href: '#', icon: '📋' },
  { label: 'Search',   href: '#', icon: '🔍' },
  { label: 'Settings', href: '#', icon: '⚙️' },
]

function App() {
  const [navOpen, setNavOpen] = useState(true)
  const year = new Date().getFullYear()

  return (
    <div className={`layout ${navOpen ? 'nav-open' : 'nav-closed'}`}>
      <nav className="sidebar">
        <button
          className="burger"
          onClick={() => setNavOpen((o) => !o)}
          aria-label={navOpen ? 'Close navigation' : 'Open navigation'}
        >
          <span /><span /><span />
        </button>
        <ul className="nav-links">
          {NAV_ITEMS.map((item) => (
            <li key={item.label}>
              <a href={item.href}>
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="main-wrap">
        <main className="main">
          <div className="wip-badge">WIP</div>
          <h1>Piano Lead Finder</h1>
          <p>Site under construction. Check back soon.</p>
        </main>

        <footer className="footer">
          <p>&copy; {year} Piano Lead Finder. All rights reserved.</p>
        </footer>
      </div>
    </div>
  )
}

export default App
