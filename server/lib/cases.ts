import { fail, type ActionRunContext } from "@agent-native/core/action";
import { accessFilter } from "@agent-native/core/sharing";
import { and, eq } from "drizzle-orm";

import { getDb, schema } from "../db/index.js";

export const RISK_TYPES = [
  "grooming",
  "bullying",
  "scam",
  "self_harm",
  "explicit_content",
] as const;
export const STEP_KINDS = [
  "talk",
  "evidence",
  "block",
  "report",
  "support",
  "follow_up",
] as const;
export const DRAFT_KINDS = [
  "talk_script",
  "report_text",
  "case_summary",
] as const;

/** The agent loop calls actions as "tool"; everything else is the parent. */
export function actorFor(ctx?: ActionRunContext): "agent" | "parent" {
  return ctx?.caller === "tool" ? "agent" : "parent";
}

export function nowIso() {
  return new Date().toISOString();
}

export function requireEmail(ctx?: ActionRunContext): string {
  return (
    ctx?.userEmail ??
    fail("Sign in to use the family desk.", { statusCode: 401 })
  );
}

/** Loads a case the caller can see, or fails with 404. */
export async function loadCase(caseId: string) {
  const { cases, caseShares } = schema;
  const [row] = await getDb()
    .select({
      id: cases.id,
      orgId: cases.orgId,
      status: cases.status,
      childAlias: cases.childAlias,
      riskType: cases.riskType,
    })
    .from(cases)
    .where(and(eq(cases.id, caseId), accessFilter(cases, caseShares)))
    .limit(1);
  if (!row)
    fail("Case not found.", { errorCode: "not_found", statusCode: 404 });
  return row;
}

export function assertOpen(status: string) {
  if (status === "closed")
    fail("This case is closed. Reopen is not supported in this version.", {
      errorCode: "case_closed",
      statusCode: 409,
    });
}

export async function logEvent(
  caseId: string,
  orgId: string | null,
  ownerEmail: string,
  actor: "agent" | "parent" | "night_guard",
  message: string,
) {
  await getDb()
    .insert(schema.caseEvents)
    .values({
      id: crypto.randomUUID(),
      caseId,
      actor,
      message: message.slice(0, 500),
      ownerEmail,
      orgId,
      createdAt: nowIso(),
    });
}
