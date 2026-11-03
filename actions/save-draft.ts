import { defineAction, fail } from "@agent-native/core/action";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import {
  actorFor,
  assertOpen,
  DRAFT_KINDS,
  loadCase,
  logEvent,
  nowIso,
  requireEmail,
} from "../server/lib/cases.js";

const LABEL: Record<string, string> = {
  talk_script: "conversation script",
  report_text: "report text",
  case_summary: "case summary",
};

export default defineAction({
  description:
    "Write or replace one draft of a case: talk_script (how the parent opens a calm, no-blame conversation), report_text (text the parent can paste into SaferNet, NCMEC CyberTipline or the app's report form) or case_summary (dated record of what happened and what was done). Any save returns the draft to 'draft' status until the parent approves it. Never include the full chat; only the flagged phrase is known.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    kind: z.enum(DRAFT_KINDS).describe("Which draft"),
    body: z
      .string()
      .min(1)
      .max(6000)
      .describe("Full draft text in plain language; markdown lists allowed"),
  }),
  outputSchema: z.object({ id: z.string(), kind: z.string(), status: z.string() }),
  mcpAnnotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
  run: async ({ caseId, kind, body }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    const actor = actorFor(ctx);
    const d = schema.caseDrafts;
    const now = nowIso();
    const [row] = await getDb()
      .insert(d)
      .values({
        id: crypto.randomUUID(),
        caseId,
        kind,
        body,
        status: "draft",
        lastEditedBy: actor,
        ownerEmail: email,
        orgId: c.orgId,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: [d.caseId, d.kind],
        set: { body, status: "draft", lastEditedBy: actor, updatedAt: now },
      })
      .returning({ id: d.id });
    if (!row) fail("Could not save the draft.", { statusCode: 500 });
    await logEvent(
      caseId,
      c.orgId,
      email,
      actor,
      `${actor === "agent" ? "Agent drafted" : "Parent edited"} the ${LABEL[kind]}.`,
    );
    return { id: row.id, kind, status: "draft" };
  },
});
