import {
  IconBan,
  IconCalendarEvent,
  IconCamera,
  IconFlag,
  IconHeartHandshake,
  IconMessageCircle,
} from "@tabler/icons-react";

export const RISK_LABEL: Record<string, string> = {
  grooming: "Possible grooming",
  bullying: "Bullying",
  scam: "Scam attempt",
  self_harm: "Self-harm signal",
  explicit_content: "Explicit content",
};

export const SEVERITY_CLASS: Record<string, string> = {
  high: "bg-red-500/12 text-red-700 dark:text-red-300 border-red-500/30",
  medium:
    "bg-amber-500/12 text-amber-800 dark:text-amber-300 border-amber-500/30",
  low: "bg-sky-500/12 text-sky-800 dark:text-sky-300 border-sky-500/30",
};

export const STEP_KIND = {
  talk: { label: "Talk", Icon: IconMessageCircle },
  evidence: { label: "Evidence", Icon: IconCamera },
  block: { label: "Block", Icon: IconBan },
  report: { label: "Report", Icon: IconFlag },
  support: { label: "Support", Icon: IconHeartHandshake },
  follow_up: { label: "Follow-up", Icon: IconCalendarEvent },
} as const;

export const STEP_STATUS = {
  proposed: {
    label: "Waiting for you",
    className:
      "bg-amber-500/12 text-amber-800 dark:text-amber-300 border-amber-500/30",
  },
  approved: {
    label: "Approved",
    className:
      "bg-emerald-500/12 text-emerald-800 dark:text-emerald-300 border-emerald-500/30",
  },
  done: {
    label: "Done",
    className: "bg-muted text-muted-foreground border-border",
  },
  skipped: {
    label: "Skipped",
    className: "bg-muted text-muted-foreground border-border line-through",
  },
} as const;

export function stepStatus(status: string) {
  return (
    STEP_STATUS[status as keyof typeof STEP_STATUS] ?? STEP_STATUS.proposed
  );
}

export const DRAFT_LABEL: Record<string, string> = {
  talk_script: "Talk script",
  report_text: "Report text",
  case_summary: "Case summary",
};

export function when(iso: string) {
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Fictional alerts for the demo. No real child, chat or account. */
export const DEMO_ALERTS = [
  {
    label: "Lia · Roblox · possible grooming",
    payload: {
      childAlias: "Lia",
      app: "Roblox",
      riskType: "grooming",
      severity: "high",
      flaggedPhrase:
        "you're really mature for 11. let's keep this our secret and talk on another app",
    },
  },
  {
    label: "Theo · Discord · bullying",
    payload: {
      childAlias: "Theo",
      app: "Discord",
      riskType: "bullying",
      severity: "medium",
      flaggedPhrase: "nobody in the server wants you here, just leave already",
    },
  },
  {
    label: "Lia · Roblox · scam",
    payload: {
      childAlias: "Lia",
      app: "Roblox",
      riskType: "scam",
      severity: "low",
      flaggedPhrase:
        "give me your password and I'll send you 10,000 free Robux",
    },
  },
] as const;

/** What a careless integration might send. The desk must refuse it. */
export const LEAKY_ALERT = {
  childAlias: "Lia",
  app: "Roblox",
  riskType: "grooming",
  severity: "high",
  flaggedPhrase: "let's keep this our secret",
  transcript: "[the whole private conversation would be here]",
};
