import { describe, expect, it } from "vitest";

import {
  checkAlertPrivacy,
  firstUnreviewed,
  guidanceFor,
  MAX_PHRASE_LENGTH,
  nextStepStatus,
  statusAfterEdit,
} from "../server/lib/case-rules";

const alert = {
  childAlias: "Lia",
  app: "Roblox",
  riskType: "grooming",
  severity: "high",
  flaggedPhrase: "let's keep this our secret",
};

describe("checkAlertPrivacy", () => {
  it("accepts the fields Night Guard is allowed to share", () => {
    expect(checkAlertPrivacy(alert)).toEqual({
      ok: true,
      phrase: "let's keep this our secret",
    });
  });

  it("refuses a payload that carries the full chat", () => {
    const result = checkAlertPrivacy({
      ...alert,
      transcript: "the whole conversation",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toContain("transcript");
  });

  it("refuses a multi-line phrase, which is a transcript in disguise", () => {
    expect(
      checkAlertPrivacy({
        ...alert,
        flaggedPhrase: "hi\nlet's keep this our secret",
      }).ok,
    ).toBe(false);
  });

  it("refuses a phrase longer than the limit", () => {
    const long = "a".repeat(MAX_PHRASE_LENGTH + 1);
    expect(checkAlertPrivacy({ ...alert, flaggedPhrase: long }).ok).toBe(false);
  });

  it("trims the phrase it keeps", () => {
    const result = checkAlertPrivacy({
      ...alert,
      flaggedPhrase: "  send me a photo  ",
    });
    expect(result).toEqual({ ok: true, phrase: "send me a photo" });
  });
});

describe("nextStepStatus", () => {
  it("lets the parent approve, skip and finish steps in order", () => {
    expect(nextStepStatus("approve", "proposed")).toBe("approved");
    expect(nextStepStatus("done", "approved")).toBe("done");
    expect(nextStepStatus("skip", "proposed")).toBe("skipped");
  });

  it("never marks a step done before it is approved", () => {
    expect(nextStepStatus("done", "proposed")).toBeNull();
    expect(nextStepStatus("done", "skipped")).toBeNull();
  });

  it("reopens finished or skipped steps", () => {
    expect(nextStepStatus("reopen", "done")).toBe("approved");
    expect(nextStepStatus("reopen", "skipped")).toBe("proposed");
  });
});

describe("statusAfterEdit", () => {
  it("sends an approved step back for review when the agent edits it", () => {
    expect(statusAfterEdit("agent", "approved")).toBe("proposed");
  });

  it("keeps the status when the parent edits", () => {
    expect(statusAfterEdit("parent", "approved")).toBe("approved");
  });
});

describe("guidanceFor", () => {
  it("always includes evidence and reporting for grooming", () => {
    const g = guidanceFor("grooming");
    expect(g.stepKinds).toEqual(expect.arrayContaining(["evidence", "report"]));
    expect(g.reportTo.join(" ")).toContain("report.cybertip.org");
    expect(g.reportTo.join(" ")).toContain("safernet");
  });

  it("points self-harm signals to crisis lines, not to a police report first", () => {
    const g = guidanceFor("self_harm");
    expect(g.stepKinds).toContain("support");
    expect(g.stepKinds).not.toContain("report");
    expect(g.reportTo.join(" ")).toContain("188");
  });

  it("falls back to a safe default for an unknown risk", () => {
    expect(guidanceFor("something_new").stepKinds[0]).toBe("talk");
  });
});

describe("firstUnreviewed", () => {
  it("finds the step that still waits for the parent", () => {
    const steps = [
      { title: "Talk", status: "done" },
      { title: "Report", status: "proposed" },
    ];
    expect(firstUnreviewed(steps)?.title).toBe("Report");
    expect(
      firstUnreviewed([{ title: "Talk", status: "approved" }]),
    ).toBeUndefined();
  });
});
