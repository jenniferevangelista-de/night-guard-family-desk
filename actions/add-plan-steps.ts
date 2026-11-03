import { defineAction } from "@agent-native/core/action";
import { max as sqlMax, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import {
  actorFor,
  assertOpen,
  loadCase,
  logEvent,
  nowIso,
  requireEmail,
  STEP_KINDS,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Add plan steps to a case in one call. Steps start as 'proposed' and only the parent can approve them in the case screen. Use kinds: talk (calm conversation, no punishment), evidence (what to keep), block, report (SaferNet, NCMEC, in-app report), support, follow_up.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    steps: z
      .array(
        z.object({
          kind: z.enum(STEP_KINDS).describe("Step category"),
          title: z.string().min(1).max(120).describe("Short imperative title"),
          detail: z
            .string()
            .min(1)
            .max(1200)
            .describe("What to do and why, in plain words for a parent"),
        }),
      )
      .min(1)
      .max(8)
      .describe("Ordered steps to append"),
  }),
  outputSchema: z.object({
    caseId: z.string(),
    added: z.array(z.object({ id: z.string(), title: z.string() })),
  }),
  mcpAnnotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
  run: async ({ caseId, steps }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    const actor = actorFor(ctx);
    const s = schema.caseSteps;
    const [agg] = await getDb()
      .select({ top: sqlMax(s.position) })
      .from(s)
      .where(eq(s.caseId, caseId));
    let position = Number(agg?.top ?? 0);
    const rows = steps.map((step) => ({
      id: crypto.randomUUID(),
      caseId,
      kind: step.kind,
      title: step.title,
      detail: step.detail,
      status: "proposed" as const,
      proposedBy: actor,
      position: ++position,
      ownerEmail: email,
      orgId: c.orgId,
      updatedAt: nowIso(),
    }));
    await getDb().insert(s).values(rows);
    await logEvent(
      caseId,
      c.orgId,
      email,
      actor,
      `${actor === "agent" ? "Agent" : "Parent"} proposed ${rows.length} step(s): ${rows.map((r) => r.title).join("; ")}`,
    );
    return { caseId, added: rows.map((r) => ({ id: r.id, title: r.title })) };
  },
});
