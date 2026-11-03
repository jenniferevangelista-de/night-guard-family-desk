import { defineAction, fail } from "@agent-native/core/action";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import { nextStepStatus } from "../server/lib/case-rules.js";
import {
  assertOpen,
  loadCase,
  logEvent,
  nowIso,
  requireEmail,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Parent's decision on a plan step: approve, skip, mark done, or reopen. Only the signed-in parent can run this from the case screen; it is not available to the agent.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    stepId: z.string().describe("Step id"),
    decision: z
      .enum(["approve", "skip", "done", "reopen"])
      .describe("Decision"),
  }),
  outputSchema: z.object({ id: z.string(), status: z.string() }),
  uiOnly: true,
  run: async ({ caseId, stepId, decision }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    const s = schema.caseSteps;
    const [step] = await getDb()
      .select({ id: s.id, status: s.status, title: s.title })
      .from(s)
      .where(and(eq(s.id, stepId), eq(s.caseId, caseId)))
      .limit(1);
    if (!step)
      fail("Step not found.", { errorCode: "not_found", statusCode: 404 });
    const next = nextStepStatus(decision, step.status);
    if (!next)
      fail(
        decision === "done"
          ? "Approve this step before marking it done."
          : `Cannot ${decision} a step that is ${step.status}.`,
        { errorCode: "invalid_transition", statusCode: 409 },
      );
    await getDb()
      .update(s)
      .set({ status: next, updatedAt: nowIso() })
      .where(eq(s.id, stepId));
    const verb = {
      approve: "approved",
      skip: "skipped",
      done: "marked done",
      reopen: "reopened",
    }[decision];
    await logEvent(
      caseId,
      c.orgId,
      email,
      "parent",
      `Parent ${verb} "${step.title}".`,
    );
    return { id: stepId, status: next };
  },
});
