import { useState } from "react";
import { AuthProvider, useAuth } from "./AuthContext";
import Header from "./Header";
import "./App.css";

const NAV_ITEMS = [
  { label: "Home", href: "#", icon: "🏠" },
  { label: "Leads", href: "#", icon: "📋" },
  { label: "Search", href: "#", icon: "🔍" },
  { label: "Settings", href: "#", icon: "⚙️" },
];

function MainContent() {
  const { user } = useAuth();

  if (user === undefined) return null;

  if (!user) {
    return (
      <main className="main">
        <h1>find Piano Leads</h1>
        <p>Sign in to access the app.</p>
      </main>
    );
  }

  return (
    <main className="main">
      <h1>find Piano Leads</h1>
      <p>Welcome, {user.displayName ?? user.email}.</p>
    </main>
  );
}

function App() {
  const [navOpen, setNavOpen] = useState(true);
  const year = new Date().getFullYear();

  return (
    <AuthProvider>
      <div className={`layout ${navOpen ? "nav-open" : "nav-closed"}`}>
        <nav className="sidebar">
          <button
            className="burger"
            onClick={() => setNavOpen((o) => !o)}
            aria-label={navOpen ? "Close navigation" : "Open navigation"}
          >
            <span />
            <span />
            <span />
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
          <Header />
          <MainContent />

          <footer className="footer">
            <p>&copy; {year} Piano Leads. All rights reserved.</p>
          </footer>
        </div>
      </div>
    </AuthProvider>
  );
}

export default App;
