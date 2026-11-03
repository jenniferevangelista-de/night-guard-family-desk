import { defineAction } from "@agent-native/core/action";
import { buildDeepLink } from "@agent-native/core/server";
import { accessFilter } from "@agent-native/core/sharing";
import { desc, inArray, sql } from "drizzle-orm";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";

const caseRow = z.object({
  id: z.string(),
  childAlias: z.string(),
  app: z.string(),
  riskType: z.string(),
  severity: z.string(),
  flaggedPhrase: z.string(),
  detectedAt: z.string(),
  status: z.string(),
  stepsTotal: z.number(),
  stepsWaiting: z.number(),
  stepsDone: z.number(),
});

export default defineAction({
  description:
    "List the family's Night Guard cases, newest first, with how many plan steps wait for the parent's review.",
  schema: z.object({}),
  outputSchema: z.object({ cases: z.array(caseRow) }),
  http: { method: "GET" },
  readOnly: true,
  link: () => ({
    url: buildDeepLink({ view: "cases", to: "/cases" }),
    label: "Open cases",
  }),
  run: async () => {
    const { cases, caseShares, caseSteps } = schema;
    const rows = await getDb()
      .select({
        id: cases.id,
        childAlias: cases.childAlias,
        app: cases.app,
        riskType: cases.riskType,
        severity: cases.severity,
        flaggedPhrase: cases.flaggedPhrase,
        detectedAt: cases.detectedAt,
        status: cases.status,
      })
      .from(cases)
      .where(accessFilter(cases, caseShares))
      .orderBy(desc(cases.detectedAt))
      .limit(100);
    const ids = rows.map((r) => r.id);
    const counts = ids.length
      ? await getDb()
          .select({
            caseId: caseSteps.caseId,
            total: sql<number>`count(*)::int`,
            waiting: sql<number>`(count(*) filter (where ${caseSteps.status} = 'proposed'))::int`,
            done: sql<number>`(count(*) filter (where ${caseSteps.status} = 'done'))::int`,
          })
          .from(caseSteps)
          .where(inArray(caseSteps.caseId, ids))
          .groupBy(caseSteps.caseId)
      : [];
    const byId = new Map(counts.map((c) => [c.caseId, c]));
    return {
      cases: rows.map((r) => ({
        ...r,
        stepsTotal: Number(byId.get(r.id)?.total ?? 0),
        stepsWaiting: Number(byId.get(r.id)?.waiting ?? 0),
        stepsDone: Number(byId.get(r.id)?.done ?? 0),
      })),
    };
  },
});
