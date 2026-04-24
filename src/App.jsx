import { useState } from 'react'
import './App.css'

const NAV_ITEMS = [
  { label: 'Home', href: '#' },
  { label: 'Leads', href: '#' },
  { label: 'Search', href: '#' },
  { label: 'Settings', href: '#' },
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
        {navOpen && (
          <ul className="nav-links">
            {NAV_ITEMS.map((item) => (
              <li key={item.label}>
                <a href={item.href}>{item.label}</a>
              </li>
            ))}
          </ul>
        )}
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
