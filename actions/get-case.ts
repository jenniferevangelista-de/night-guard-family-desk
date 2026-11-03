import { defineAction, fail } from "@agent-native/core/action";
import { buildDeepLink } from "@agent-native/core/server";
import { asc, desc, eq } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import { loadCase } from "../server/lib/cases.js";

export default defineAction({
  description:
    "Read one case: the Night Guard alert (risk type, app and the one flagged phrase; the full chat is never available), the plan steps with their review status, the drafts and the case log.",
  schema: z.object({ caseId: z.string().describe("Case id from list-cases") }),
  outputSchema: z.object({
    case: z.object({
      id: z.string(),
      childAlias: z.string(),
      app: z.string(),
      riskType: z.string(),
      severity: z.string(),
      flaggedPhrase: z.string(),
      detectedAt: z.string(),
      status: z.string(),
      closingNote: z.string().nullable(),
    }),
    steps: z.array(
      z.object({
        id: z.string(),
        kind: z.string(),
        title: z.string(),
        detail: z.string(),
        status: z.string(),
        proposedBy: z.string(),
        editedBy: z.string().nullable(),
        position: z.number(),
      }),
    ),
    drafts: z.array(
      z.object({
        id: z.string(),
        kind: z.string(),
        body: z.string(),
        status: z.string(),
        lastEditedBy: z.string(),
        updatedAt: z.string(),
      }),
    ),
    events: z.array(
      z.object({
        id: z.string(),
        actor: z.string(),
        message: z.string(),
        createdAt: z.string(),
      }),
    ),
  }),
  http: { method: "GET" },
  readOnly: true,
  link: ({ args }) => ({
    url: buildDeepLink({
      view: "cases",
      to: `/cases/${encodeURIComponent(args.caseId)}`,
      params: { caseId: args.caseId },
    }),
    label: "Open case",
  }),
  run: async ({ caseId }) => {
    await loadCase(caseId);
    const { cases, caseSteps, caseDrafts, caseEvents } = schema;
    const db = getDb();
    const [c] = await db
      .select({
        id: cases.id,
        childAlias: cases.childAlias,
        app: cases.app,
        riskType: cases.riskType,
        severity: cases.severity,
        flaggedPhrase: cases.flaggedPhrase,
        detectedAt: cases.detectedAt,
        status: cases.status,
        closingNote: cases.closingNote,
      })
      .from(cases)
      .where(eq(cases.id, caseId))
      .limit(1);
    if (!c) fail("Case not found.", { errorCode: "not_found", statusCode: 404 });
    const steps = await db
      .select({
        id: caseSteps.id,
        kind: caseSteps.kind,
        title: caseSteps.title,
        detail: caseSteps.detail,
        status: caseSteps.status,
        proposedBy: caseSteps.proposedBy,
        editedBy: caseSteps.editedBy,
        position: caseSteps.position,
      })
      .from(caseSteps)
      .where(eq(caseSteps.caseId, caseId))
      .orderBy(asc(caseSteps.position))
      .limit(50);
    const drafts = await db
      .select({
        id: caseDrafts.id,
        kind: caseDrafts.kind,
        body: caseDrafts.body,
        status: caseDrafts.status,
        lastEditedBy: caseDrafts.lastEditedBy,
        updatedAt: caseDrafts.updatedAt,
      })
      .from(caseDrafts)
      .where(eq(caseDrafts.caseId, caseId))
      .limit(10);
    const events = await db
      .select({
        id: caseEvents.id,
        actor: caseEvents.actor,
        message: caseEvents.message,
        createdAt: caseEvents.createdAt,
      })
      .from(caseEvents)
      .where(eq(caseEvents.caseId, caseId))
      .orderBy(desc(caseEvents.createdAt))
      .limit(100);
    return { case: c, steps, drafts, events };
  },
});
