import { defineAction, fail } from "@agent-native/core/action";
import { and, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import {
  assertOpen,
  DRAFT_KINDS,
  loadCase,
  logEvent,
  nowIso,
  requireEmail,
} from "../server/lib/cases.js";

export default defineAction({
  description:
    "Parent approves a draft as ready to use. Only the signed-in parent can run this from the case screen.",
  schema: z.object({
    caseId: z.string().describe("Case id"),
    kind: z.enum(DRAFT_KINDS).describe("Which draft"),
  }),
  outputSchema: z.object({ kind: z.string(), status: z.string() }),
  uiOnly: true,
  run: async ({ caseId, kind }, ctx) => {
    const email = requireEmail(ctx);
    const c = await loadCase(caseId);
    assertOpen(c.status);
    const d = schema.caseDrafts;
    const [row] = await getDb()
      .update(d)
      .set({ status: "approved", updatedAt: nowIso() })
      .where(and(eq(d.caseId, caseId), eq(d.kind, kind)))
      .returning({ id: d.id });
    if (!row) fail("Draft not found.", { errorCode: "not_found", statusCode: 404 });
    await logEvent(caseId, c.orgId, email, "parent", `Parent approved the ${kind.replace("_", " ")}.`);
    return { kind, status: "approved" };
  },
});
