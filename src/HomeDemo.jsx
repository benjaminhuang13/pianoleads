import { useState, useEffect } from "react";
import "./HomeDemo.css";

const CITY = "Piano";
const FAKE_LEADS = [
  { name: "NYC Piano Lessons",   rating: "4.7", reviews: 21 },
  { name: "Jane Mitchell Piano Studio", rating: "4.9", reviews: 38 },
  { name: "Sara Okonkwo Music School",  rating: "5.0", reviews: 14 },
];

const PHASES = ["typing", "searching", "results", "pause"];
const PHASE_MS = { typing: CITY.length * 80, searching: 1100, results: 2800, pause: 800 };

export default function HomeDemo() {
  const [phase, setPhase]       = useState("typing");
  const [typed, setTyped]       = useState("");
  const [visible, setVisible]   = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      while (!cancelled) {
        // type city
        setPhase("typing");
        setTyped("");
        setVisible(0);
        for (let i = 1; i <= CITY.length; i++) {
          await delay(80);
          if (cancelled) return;
          setTyped(CITY.slice(0, i));
        }

        // searching
        setPhase("searching");
        await delay(PHASE_MS.searching);
        if (cancelled) return;

        // reveal leads one by one
        setPhase("results");
        for (let i = 1; i <= FAKE_LEADS.length; i++) {
          await delay(420);
          if (cancelled) return;
          setVisible(i);
        }

        // hold, then restart
        await delay(PHASE_MS.results);
        if (cancelled) return;

        // fade out pause
        setPhase("pause");
        await delay(PHASE_MS.pause);
        if (cancelled) return;
      }
    }

    run();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="demo-shell" aria-hidden="true">
      <div className="demo-bar">
        <span className="demo-dot" />
        <span className="demo-dot" />
        <span className="demo-dot" />
      </div>

      <div className="demo-search-row">
        <span className="demo-search-icon">🔍</span>
        <span className="demo-input">
          {typed}
          <span className="demo-cursor" />
        </span>
        <span className={`demo-btn${phase === "searching" ? " searching" : ""}`}>
          {phase === "searching" ? "Searching…" : "Find Leads"}
        </span>
      </div>

      <div className="demo-results">
        {phase === "results" || phase === "pause"
          ? FAKE_LEADS.map((lead, i) => (
              <div
                key={lead.name}
                className={`demo-lead${i < visible ? " demo-lead--in" : ""}`}
              >
                <span className="demo-lead-name">{lead.name}</span>
                <span className="demo-lead-meta">Piano Teacher</span>
                <span className="demo-lead-rating">★ {lead.rating} · {lead.reviews} reviews</span>
              </div>
            ))
          : null}
      </div>
    </div>
  );
}

function delay(ms) {
  return new Promise((res) => setTimeout(res, ms));
}
