import { defineAction, fail } from "@agent-native/core/action";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import {
  actorFor,
  assertOpen,
  loadCase,
  logEvent,
  requireEmail,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Close a case with a short closing note. Fails with unreviewed_steps while any step is still 'proposed'. When the agent asks to close, the parent must approve the call in chat.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    closingNote: z
      .string()
      .min(1)
      .max(600)
      .describe("One or two sentences: outcome and any follow-up date"),
  }),
  outputSchema: z.object({ id: z.string(), status: z.string() }),
  // The agent can suggest closing, but a person always confirms it.
  needsApproval: (_args, ctx) => ctx?.caller === "tool",
  mcpAnnotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
  run: async ({ caseId, closingNote }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    const s = schema.caseSteps;
    const [waiting] = await getDb()
      .select({ id: s.id, title: s.title })
      .from(s)
      .where(and(eq(s.caseId, caseId), eq(s.status, "proposed")))
      .limit(1);
    if (waiting)
      fail(`Review every step first. Still waiting: "${waiting.title}".`, {
        errorCode: "unreviewed_steps",
        statusCode: 409,
      });
    await getDb()
      .update(schema.cases)
      .set({ status: "closed", closingNote })
      .where(eq(schema.cases.id, caseId));
    await logEvent(caseId, c.orgId, email, actorFor(ctx), `Case closed: ${closingNote}`);
    return { id: caseId, status: "closed" };
  },
});
