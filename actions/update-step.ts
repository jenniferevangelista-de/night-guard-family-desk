import { defineAction, fail } from "@agent-native/core/action";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import { statusAfterEdit } from "../server/lib/case-rules.js";
import {
  actorFor,
  assertOpen,
  loadCase,
  logEvent,
  nowIso,
  requireEmail,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Edit the title or detail of a plan step. When the agent edits a step the parent already approved, the step goes back to 'proposed' and needs the parent's approval again.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    stepId: z.string().describe("Step id from get-case"),
    title: z.string().min(1).max(120).optional().describe("New title"),
    detail: z.string().min(1).max(1200).optional().describe("New detail"),
  }),
  outputSchema: z.object({
    id: z.string(),
    status: z.string(),
    needsReapproval: z.boolean(),
  }),
  mcpAnnotations: {
    readOnlyHint: false,
    destructiveHint: true,
    openWorldHint: false,
  },
  run: async ({ caseId, stepId, title, detail }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    if (!title && !detail)
      fail("Nothing to change: pass title or detail.", {
        errorCode: "empty_patch",
      });
    const actor = actorFor(ctx);
    const s = schema.caseSteps;
    const [step] = await getDb()
      .select({ id: s.id, status: s.status, title: s.title })
      .from(s)
      .where(and(eq(s.id, stepId), eq(s.caseId, caseId)))
      .limit(1);
    if (!step)
      fail("Step not found.", { errorCode: "not_found", statusCode: 404 });
    if (step.status === "done")
      fail("This step is already done; add a follow-up step instead.", {
        errorCode: "step_done",
        statusCode: 409,
      });
    const status = statusAfterEdit(actor, step.status);
    const needsReapproval = status !== step.status;
    await getDb()
      .update(s)
      .set({
        ...(title ? { title } : {}),
        ...(detail ? { detail } : {}),
        status,
        editedBy: actor,
        updatedAt: nowIso(),
      })
      .where(eq(s.id, stepId));
    await logEvent(
      caseId,
      c.orgId,
      email,
      actor,
      needsReapproval
        ? `Agent edited approved step "${title ?? step.title}"; it waits for the parent's approval again.`
        : `${actor === "agent" ? "Agent" : "Parent"} edited step "${title ?? step.title}".`,
    );
    return { id: stepId, status, needsReapproval };
  },
});
