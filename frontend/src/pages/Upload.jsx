import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export default function Upload() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      const run = await api.startRun(doc.id);
      navigate(`/courtroom/${run.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page center">
      <div className="card upload-card">
        <h1>⚖️ RedTeam Court</h1>
        <p className="subtitle">
          Upload a strategic document. Five adversarial agents — CFO, Legal,
          Competitor, Market, Execution — will attack it, debate it, and
          deliver a verdict.
        </p>
        <form onSubmit={submit}>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <button type="submit" disabled={!file || busy}>
            {busy ? "Convening the court..." : "Convene the Court"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
