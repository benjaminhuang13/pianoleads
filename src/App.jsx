import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./AuthContext";
import Header from "./Header";
import LeadsPage from "./leads/LeadsPage";
import HomeDemo from "./HomeDemo";
import "./App.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000 } },
});

const NAV_ITEMS = [
  { id: "home", label: "Home", icon: "🏠" },
  { id: "leads", label: "Leads", icon: "📋", requiresAuth: true },
];

function AppContent() {
  const { user, isVerifying } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const [activePage, setActivePage] = useState(() => {
    const hash = window.location.hash.slice(1);
    return NAV_ITEMS.some((i) => i.id === hash) ? hash : "home";
  });

  function handleNav(id) {
    window.location.hash = id;
    setActivePage(id);
  }
  const year = new Date().getFullYear();

  function renderPage() {
    if (user === undefined || isVerifying) return null;

    if (!user) {
      return (
        <main className="main">
          <h1>find Piano Leads 🔍</h1>
          <div className="home-body">
            <div className="home-features-col">
              <p className="home-cta">Invite only.</p>
              <p className="home-cta">Sign in to get started.</p>
              <ul className="home-features">
                <li>Search for piano teachers in any area</li>
                <li>Save and manage leads in an organized list</li>
                <li>Track outreach status for each contact</li>
                <li>
                  Pulls data from Google Maps, Yelp, MTNA, social media, and
                  more
                </li>
                <li>Filter by territory, status, source, assignee, and more</li>
                <li>Export leads to CSV</li>
              </ul>
            </div>
            <HomeDemo />
          </div>
        </main>
      );
    }

    if (activePage === "leads") return <LeadsPage />;

    return (
      <main className="main">
        <h1>find Piano Leads 🔍</h1>
        <div className="home-body">
          <div className="home-features-col">
            <p className="home-tagline">
              Welcome, {user.displayName ?? user.email}.
            </p>
            <ul className="home-features">
              <li>Search for piano teachers in any area</li>
              <li>Save and manage leads in an organized list</li>
              <li>Track outreach status for each contact</li>
              <li>Filter by territory, status, or source</li>
              <li>Export leads to CSV</li>
            </ul>
            <p className="home-cta">
              Head to{" "}
              <button
                className="inline-link"
                onClick={() => handleNav("leads")}
              >
                Leads
              </button>{" "}
              to get started.
            </p>
          </div>
          <HomeDemo />
        </div>
      </main>
    );
  }

  return (
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
          {NAV_ITEMS.filter((item) => !item.requiresAuth || user).map(
            (item) => (
              <li key={item.id}>
                <button
                  className={`nav-btn${activePage === item.id ? " nav-active" : ""}`}
                  onClick={() => handleNav(item.id)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </button>
              </li>
            ),
          )}
        </ul>
      </nav>

      <div className="main-wrap">
        <Header />
        {renderPage()}
        <footer className="footer">
          <p>&copy; {year} Piano Leads. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
