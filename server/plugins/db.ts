import { runMigrations } from "@agent-native/core/db";

export default runMigrations(
  [
    {
      version: 1,
      name: "family-desk-cases",
      sql: `CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY,
  child_alias TEXT NOT NULL,
  app TEXT NOT NULL,
  risk_type TEXT NOT NULL CHECK (risk_type IN ('grooming', 'bullying', 'scam', 'self_harm', 'explicit_content')),
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
  flagged_phrase TEXT NOT NULL CHECK (char_length(flagged_phrase) <= 240),
  detected_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  closing_note TEXT,
  created_at TEXT NOT NULL DEFAULT (now()),
  owner_email TEXT NOT NULL DEFAULT 'local@localhost',
  org_id TEXT,
  visibility TEXT NOT NULL DEFAULT 'private'
);
CREATE TABLE IF NOT EXISTS case_shares (
  id TEXT PRIMARY KEY,
  resource_id TEXT NOT NULL,
  principal_type TEXT NOT NULL,
  principal_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'viewer',
  created_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (now()),
  notified_at TEXT
);
CREATE TABLE IF NOT EXISTS case_steps (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  kind TEXT NOT NULL CHECK (kind IN ('talk', 'evidence', 'block', 'report', 'support', 'follow_up')),
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'done', 'skipped')),
  proposed_by TEXT NOT NULL CHECK (proposed_by IN ('agent', 'parent')),
  edited_by TEXT CHECK (edited_by IN ('agent', 'parent')),
  position INTEGER NOT NULL,
  owner_email TEXT NOT NULL,
  org_id TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_drafts (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  kind TEXT NOT NULL CHECK (kind IN ('talk_script', 'report_text', 'case_summary')),
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved')),
  last_edited_by TEXT NOT NULL CHECK (last_edited_by IN ('agent', 'parent')),
  owner_email TEXT NOT NULL,
  org_id TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE (case_id, kind)
);
CREATE TABLE IF NOT EXISTS case_events (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  actor TEXT NOT NULL CHECK (actor IN ('agent', 'parent', 'night_guard')),
  message TEXT NOT NULL,
  owner_email TEXT NOT NULL,
  org_id TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS cases_owner_org_created_idx ON cases (owner_email, org_id, created_at);
CREATE INDEX IF NOT EXISTS case_shares_resource_idx ON case_shares (resource_id, principal_type, principal_id);
CREATE INDEX IF NOT EXISTS case_steps_case_idx ON case_steps (case_id, position);
CREATE INDEX IF NOT EXISTS case_events_case_idx ON case_events (case_id, created_at)`,
    },
  ],
  { table: "family_desk_migrations" },
);
