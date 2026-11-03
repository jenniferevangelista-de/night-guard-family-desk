import { defineAction } from "@agent-native/core/action";
import { z } from "zod";

import {
  actorFor,
  loadCase,
  logEvent,
  requireEmail,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Append a dated note to the case log, for example what the child said in the conversation or that a report was filed (with its protocol number).",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    note: z.string().min(1).max(500).describe("The note, one or two sentences"),
  }),
  outputSchema: z.object({ caseId: z.string() }),
  mcpAnnotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
  run: async ({ caseId, note }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    await logEvent(caseId, c.orgId, email, actorFor(ctx), note);
    return { caseId };
  },
});
