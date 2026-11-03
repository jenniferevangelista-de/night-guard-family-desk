/**
 * The family desk's rules, kept free of I/O so they can be unit tested.
 * Actions call these; the database and the UI never re-implement them.
 */

/** The only fields Night Guard may send. The full chat is never one of them. */
export const ALERT_FIELDS = [
  "childAlias",
  "app",
  "riskType",
  "severity",
  "flaggedPhrase",
  "detectedAt",
] as const;

export const MAX_PHRASE_LENGTH = 240;

export type PrivacyCheck =
  | { ok: true; phrase: string }
  | { ok: false; reason: string };

/**
 * Night Guard shares the risk, the app and one flagged phrase. Anything more
 * (a transcript, screenshots, the other person's messages) is refused.
 */
export function checkAlertPrivacy(
  payload: Record<string, unknown>,
): PrivacyCheck {
  const allowed = new Set<string>(ALERT_FIELDS);
  const extra = Object.keys(payload).filter((key) => !allowed.has(key));
  if (extra.length > 0) {
    return {
      ok: false,
      reason: `Refused: Night Guard may only share risk type, app and the flagged phrase. Extra fields: ${extra.join(", ")}.`,
    };
  }
  const phrase = String(payload.flaggedPhrase ?? "").trim();
  if (!phrase)
    return { ok: false, reason: "Refused: the flagged phrase is empty." };
  if (phrase.length > MAX_PHRASE_LENGTH || /[\r\n]/.test(phrase)) {
    return {
      ok: false,
      reason: `Refused: the flagged phrase must be one line of at most ${MAX_PHRASE_LENGTH} characters, never a chat transcript.`,
    };
  }
  return { ok: true, phrase };
}

export type StepStatus = "proposed" | "approved" | "done" | "skipped";
export type Decision = "approve" | "skip" | "done" | "reopen";

const TRANSITIONS: Record<Decision, Partial<Record<StepStatus, StepStatus>>> = {
  approve: { proposed: "approved", skipped: "approved" },
  skip: { proposed: "skipped", approved: "skipped" },
  done: { approved: "done" },
  reopen: { done: "approved", skipped: "proposed", approved: "proposed" },
};

/** The parent's decision on a step, or null when it is not allowed. */
export function nextStepStatus(
  decision: Decision,
  current: StepStatus,
): StepStatus | null {
  return TRANSITIONS[decision][current] ?? null;
}

/**
 * Status after an edit. When the agent changes a step the parent already
 * approved, the parent has to approve it again.
 */
export function statusAfterEdit(
  actor: "agent" | "parent",
  current: StepStatus,
): StepStatus {
  return actor === "agent" && current === "approved" ? "proposed" : current;
}

export type Guidance = {
  /** Step kinds a good plan for this risk includes, in a sensible order. */
  stepKinds: string[];
  /** Where to report, when reporting applies. */
  reportTo: string[];
  /** One or two sentences the agent should keep in mind. */
  notes: string;
};

const REPORT_CHANNELS = [
  "The app's own Report and Block on the profile",
  "SaferNet Brasil: https://new.safernet.org.br/denuncie (anonymous)",
  "NCMEC CyberTipline: https://report.cybertip.org",
  "Immediate danger: police, 190 in Brazil or 911 in the US",
];

const GUIDANCE: Record<string, Guidance> = {
  grooming: {
    stepKinds: ["talk", "evidence", "block", "report", "follow_up"],
    reportTo: REPORT_CHANNELS,
    notes:
      "Secrecy and moving to another app are classic grooming signs. Save the username, date and the flagged message before blocking. Never contact the other person.",
  },
  explicit_content: {
    stepKinds: ["talk", "evidence", "block", "report", "support"],
    reportTo: REPORT_CHANNELS,
    notes:
      "Do not forward or save the image itself; record where and when it appeared. If a minor is shown, report it.",
  },
  bullying: {
    stepKinds: ["talk", "evidence", "block", "support", "follow_up"],
    reportTo: [REPORT_CHANNELS[0]!, "The school, if classmates are involved"],
    notes:
      "Reassure the child it is not their fault. Keep screenshots; involve the school when classmates are involved.",
  },
  scam: {
    stepKinds: ["talk", "block", "follow_up"],
    reportTo: [REPORT_CHANNELS[0]!],
    notes:
      "Never share passwords. Change the password and turn on 2-step verification. Usually no police report.",
  },
  self_harm: {
    stepKinds: ["talk", "support", "follow_up"],
    reportTo: [
      "CVV 188 in Brazil (24 h)",
      "988 Suicide & Crisis Lifeline in the US",
      "Immediate danger: 190 or 911",
    ],
    notes:
      "Talk gently today and do not leave the child alone if they may be in danger. Suggest professional help.",
  },
};

/** What a plan for this risk should cover; the agent reads it through get-case. */
export function guidanceFor(riskType: string): Guidance {
  return GUIDANCE[riskType] ?? GUIDANCE.bullying!;
}

/** A case closes only once every step has been reviewed by the parent. */
export function firstUnreviewed<T extends { status: string; title: string }>(
  steps: T[],
): T | undefined {
  return steps.find((step) => step.status === "proposed");
}
