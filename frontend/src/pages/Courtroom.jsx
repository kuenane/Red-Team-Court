import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";

const AGENT_LABELS = {
  cfo: "CFO", legal: "Legal", competitor: "Competitor", market: "Market", execution: "Execution",
};

export default function Courtroom() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [phase, setPhase] = useState("pending");
  const [findingsByAgent, setFindingsByAgent] = useState(
    Object.fromEntries(Object.keys(AGENT_LABELS).map((a) => [a, []]))
  );
  const [debate, setDebate] = useState([]);
  const [message, setMessage] = useState("Convening the court...");
  const sourceRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(api.streamRunUrl(runId));
    sourceRef.current = es;

    es.addEventListener("status", (e) => setPhase(JSON.parse(e.data).status));

    es.addEventListener("update", (e) => {
      const evt = JSON.parse(e.data);
      if (evt.phase) setPhase(evt.phase);
      if (evt.message) setMessage(evt.message);

      if (evt.phase === "attacking" && evt.finding_id) {
        setFindingsByAgent((prev) => ({
          ...prev,
          [evt.agent]: [...prev[evt.agent], evt],
        }));
      }
      if (evt.phase === "debating" && evt.argument) {
        setDebate((prev) => [...prev, evt]);
      }
      if (evt.phase === "complete" || evt.phase === "failed") {
        es.close();
        if (evt.phase === "complete") {
          setTimeout(() => navigate(`/verdict/${runId}`), 800);
        }
      }
    });

    return () => es.close();
  }, [runId, navigate]);

  return (
    <div className="page">
      <h1>⚖️ RedTeam Court — Session #{runId}</h1>
      <p className="phase-banner">
        <span className={`badge phase-${phase}`}>{phase}</span> {message}
      </p>

      <div className="agent-grid">
        {Object.entries(AGENT_LABELS).map(([key, label]) => (
          <div key={key} className="card agent-panel">
            <h3>{label}</h3>
            {findingsByAgent[key].length === 0 && <p className="muted">Reviewing...</p>}
            {findingsByAgent[key].map((f, i) => (
              <div key={i} className="finding">
                <div className="finding-severity">Severity {f.severity}/10</div>
                <div>{f.claim}</div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {debate.length > 0 && (
        <div className="card">
          <h3>Cross-Examination</h3>
          {debate.map((d, i) => (
            <div key={i} className={`debate-turn stance-${d.stance}`}>
              <strong>{AGENT_LABELS[d.agent]}</strong> [{d.stance}]: {d.argument}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
