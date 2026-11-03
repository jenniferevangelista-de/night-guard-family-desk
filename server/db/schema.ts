import {
  createSharesTable,
  ownableColumns,
} from "@agent-native/core/db/schema";
import { sql } from "drizzle-orm";
import { integer, pgTable, text } from "drizzle-orm/pg-core";

// One case per Night Guard alert. Night Guard only ever sends the risk type,
// the app and the single flagged phrase; the full chat never leaves the
// child's computer, so there is no column that could hold it.
export const cases = pgTable("cases", {
  id: text("id").primaryKey(),
  childAlias: text("child_alias").notNull(),
  app: text("app").notNull(),
  riskType: text("risk_type", {
    enum: ["grooming", "bullying", "scam", "self_harm", "explicit_content"],
  }).notNull(),
  severity: text("severity", { enum: ["low", "medium", "high"] }).notNull(),
  flaggedPhrase: text("flagged_phrase").notNull(),
  detectedAt: text("detected_at").notNull(),
  status: text("status", { enum: ["open", "closed"] })
    .notNull()
    .default("open"),
  closingNote: text("closing_note"),
  createdAt: text("created_at")
    .notNull()
    .default(sql`now()`),
  ...ownableColumns(),
});
export const caseShares = createSharesTable("case_shares");

export const caseSteps = pgTable("case_steps", {
  id: text("id").primaryKey(),
  caseId: text("case_id").notNull(),
  kind: text("kind", {
    enum: ["talk", "evidence", "block", "report", "support", "follow_up"],
  }).notNull(),
  title: text("title").notNull(),
  detail: text("detail").notNull(),
  status: text("status", {
    enum: ["proposed", "approved", "done", "skipped"],
  })
    .notNull()
    .default("proposed"),
  proposedBy: text("proposed_by", { enum: ["agent", "parent"] }).notNull(),
  editedBy: text("edited_by", { enum: ["agent", "parent"] }),
  position: integer("position").notNull(),
  ownerEmail: text("owner_email").notNull(),
  orgId: text("org_id"),
  updatedAt: text("updated_at").notNull(),
});

export const caseDrafts = pgTable("case_drafts", {
  id: text("id").primaryKey(),
  caseId: text("case_id").notNull(),
  kind: text("kind", {
    enum: ["talk_script", "report_text", "case_summary"],
  }).notNull(),
  body: text("body").notNull(),
  status: text("status", { enum: ["draft", "approved"] })
    .notNull()
    .default("draft"),
  lastEditedBy: text("last_edited_by", { enum: ["agent", "parent"] }).notNull(),
  ownerEmail: text("owner_email").notNull(),
  orgId: text("org_id"),
  updatedAt: text("updated_at").notNull(),
});

export const caseEvents = pgTable("case_events", {
  id: text("id").primaryKey(),
  caseId: text("case_id").notNull(),
  actor: text("actor", { enum: ["agent", "parent", "night_guard"] }).notNull(),
  message: text("message").notNull(),
  ownerEmail: text("owner_email").notNull(),
  orgId: text("org_id"),
  createdAt: text("created_at").notNull(),
});
