-- RedTeam Court schema (Postgres)

CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    filename        VARCHAR(255) NOT NULL,
    mime_type       VARCHAR(64),
    raw_text        TEXT NOT NULL,
    char_count      INTEGER,
    uploaded_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE analysis_runs (
    id                  SERIAL PRIMARY KEY,
    document_id         INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    status              VARCHAR(24) DEFAULT 'pending'
                        CHECK (status IN ('pending','attacking','debating','judging','complete','failed')),
    overall_risk_score  NUMERIC(5,2),          -- 0-100, set at verdict phase
    executive_summary   TEXT,
    error_message       TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE agent_findings (
    id              SERIAL PRIMARY KEY,
    run_id          INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    agent_type      VARCHAR(24) NOT NULL
                    CHECK (agent_type IN ('cfo','legal','competitor','market','execution')),
    claim           TEXT NOT NULL,
    category        VARCHAR(64),
    severity_initial SMALLINT CHECK (severity_initial BETWEEN 1 AND 10),
    evidence_quote  TEXT,                       -- verbatim short excerpt from the uploaded doc
    evidence_location TEXT,                     -- e.g. "Section 3, para 2" or approximate offset
    confidence      NUMERIC(3,2),               -- 0.00-1.00
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE debate_turns (
    id                  SERIAL PRIMARY KEY,
    run_id              INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    round               SMALLINT DEFAULT 1,
    agent_type          VARCHAR(24) NOT NULL,
    target_finding_id   INTEGER REFERENCES agent_findings(id) ON DELETE CASCADE,
    stance              VARCHAR(12) CHECK (stance IN ('support','challenge','neutral')),
    argument            TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE final_risks (
    id                      SERIAL PRIMARY KEY,
    run_id                  INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    rank                    SMALLINT NOT NULL,
    title                   VARCHAR(255) NOT NULL,
    category                VARCHAR(64),
    severity_final          SMALLINT CHECK (severity_final BETWEEN 1 AND 10),
    rationale               TEXT,
    supporting_finding_ids  INTEGER[],
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_findings_run ON agent_findings(run_id, agent_type);
CREATE INDEX idx_debate_run ON debate_turns(run_id, round);
CREATE INDEX idx_final_risks_run ON final_risks(run_id, rank);
