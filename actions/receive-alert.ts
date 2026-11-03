import { defineAction, defineActionErrors } from "@agent-native/core/action";
import { buildDeepLink } from "@agent-native/core/server";
import { z } from "zod";

import { getDb, schema } from "../server/db/index.js";
import { logEvent, requireEmail, RISK_TYPES } from "../server/lib/cases.js";

const errors = defineActionErrors("privacy_violation");

// The only fields Night Guard is allowed to send. Anything else (a transcript,
// screenshots, the other person's messages) is refused, so the family desk can
// never become a copy of the child's private chat.
const ALLOWED = new Set([
  "childAlias",
  "app",
  "riskType",
  "severity",
  "flaggedPhrase",
  "detectedAt",
]);

export default defineAction({
  description:
    "Receive one Night Guard alert and open a case. Night Guard shares only the risk type, the app and the single flagged phrase; the full chat never leaves the child's computer. Payloads with extra fields or a long multi-line phrase are rejected with privacy_violation.",
  schema: z
    .object({
      childAlias: z
        .string()
        .min(1)
        .max(40)
        .describe("First name or nickname of the child, e.g. Lia"),
      app: z
        .string()
        .min(1)
        .max(40)
        .describe("App where the risk happened, e.g. Roblox or Discord"),
      riskType: z.enum(RISK_TYPES).describe("Risk category from Night Guard"),
      severity: z.enum(["low", "medium", "high"]).describe("Night Guard severity"),
      flaggedPhrase: z
        .string()
        .min(1)
        .describe("The single flagged phrase, at most 240 characters, one line"),
      detectedAt: z
        .string()
        .datetime({ offset: true })
        .optional()
        .describe("When Night Guard flagged it, ISO 8601 with offset; defaults to now"),
    })
    .passthrough(),
  outputSchema: z.object({ id: z.string(), childAlias: z.string() }),
  errors,
  mcpAnnotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
  link: ({ result }) => ({
    url: buildDeepLink({
      view: "cases",
      to: `/cases/${encodeURIComponent(result.id)}`,
      params: { caseId: result.id },
    }),
    label: "Open case",
  }),
  run: async (args, ctx) => {
    const ownerEmail = requireEmail(ctx);
    const extra = Object.keys(args).filter((k) => !ALLOWED.has(k));
    if (extra.length)
      errors.noWrite(
        `Refused: Night Guard may only share risk type, app and the flagged phrase. Extra fields: ${extra.join(", ")}.`,
        "privacy_violation",
        { statusCode: 422 },
      );
    const phrase = args.flaggedPhrase.trim();
    if (phrase.length > 240 || /\r|\n/.test(phrase))
      errors.noWrite(
        "Refused: the flagged phrase must be one line of at most 240 characters, never a chat transcript.",
        "privacy_violation",
        { statusCode: 422 },
      );
    const orgId = ctx?.orgId ?? null;
    const row = {
      id: crypto.randomUUID(),
      childAlias: args.childAlias,
      app: args.app,
      riskType: args.riskType,
      severity: args.severity,
      flaggedPhrase: phrase,
      detectedAt: new Date(args.detectedAt ?? Date.now()).toISOString(),
      ownerEmail,
      orgId,
      visibility: orgId ? ("org" as const) : ("private" as const),
    };
    await getDb().insert(schema.cases).values(row);
    await logEvent(
      row.id,
      orgId,
      ownerEmail,
      "night_guard",
      `Alert received: ${row.riskType.replace("_", " ")} on ${row.app} (${row.severity}). Only the flagged phrase was shared.`,
    );
    return { id: row.id, childAlias: row.childAlias };
  },
});
