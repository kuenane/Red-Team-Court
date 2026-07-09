import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";

export default function Verdict() {
  const { runId } = useParams();
  const [run, setRun] = useState(null);
  const [filterAgent, setFilterAgent] = useState("all");

  useEffect(() => {
    api.getRun(runId).then(setRun).catch(console.error);
  }, [runId]);

  if (!run) return <div className="page">Loading verdict...</div>;

  const findingById = Object.fromEntries(run.findings.map((f) => [f.id, f]));
  const visibleRisks =
    filterAgent === "all"
      ? run.final_risks
      : run.final_risks.filter((r) =>
          (r.supporting_finding_ids || []).some((id) => findingById[id]?.agent_type === filterAgent)
        );

  return (
    <div className="page">
      <h1>⚖️ Verdict — Session #{runId}</h1>

      <div className="card verdict-summary">
        <div className="risk-gauge">
          <div className="risk-score">{run.overall_risk_score ?? "—"}</div>
          <div className="muted">Overall Risk Score / 100</div>
        </div>
        <p>{run.executive_summary}</p>
      </div>

      <div className="filter-bar">
        <label>Filter by agent: </label>
        <select value={filterAgent} onChange={(e) => setFilterAgent(e.target.value)}>
          <option value="all">All</option>
          <option value="cfo">CFO</option>
          <option value="legal">Legal</option>
          <option value="competitor">Competitor</option>
          <option value="market">Market</option>
          <option value="execution">Execution</option>
        </select>
      </div>

      <table className="card">
        <thead>
          <tr><th>#</th><th>Risk</th><th>Category</th><th>Severity</th><th>Rationale & Evidence</th></tr>
        </thead>
        <tbody>
          {visibleRisks.map((r) => (
            <tr key={r.rank}>
              <td>{r.rank}</td>
              <td>{r.title}</td>
              <td>{r.category}</td>
              <td><span className={`badge sev-${r.severity_final >= 7 ? "high" : r.severity_final >= 4 ? "mid" : "low"}`}>{r.severity_final}/10</span></td>
              <td>
                <div>{r.rationale}</div>
                <ul className="evidence-list">
                  {(r.supporting_finding_ids || []).map((id) => {
                    const f = findingById[id];
                    if (!f) return null;
                    return (
                      <li key={id}>
                        <em>{f.agent_type}</em>: "{f.evidence_quote}" — {f.evidence_location}
                      </li>
                    );
                  })}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Link to="/" className="link-back">← Review another document</Link>
    </div>
  );
}
