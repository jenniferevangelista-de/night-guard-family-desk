import { sendToAgentChat } from "@agent-native/core/client/agent-chat";
import {
  actionErrorMessage,
  useActionMutation,
  useActionQuery,
} from "@agent-native/core/client/hooks";
import {
  IconArrowBackUp,
  IconCheck,
  IconChevronLeft,
  IconCopy,
  IconMoonStars,
  IconPencil,
  IconPlus,
  IconRobot,
  IconShieldLock,
  IconSparkles,
  IconUser,
  IconX,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  DRAFT_LABEL,
  RISK_LABEL,
  SEVERITY_CLASS,
  STEP_KIND,
  STEP_STATUS,
  stepStatus,
  when,
} from "@/lib/case-labels";
import { cn } from "@/lib/utils";

type Step = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  status: string;
  proposedBy: string;
  editedBy: string | null;
};
type Draft = {
  kind: string;
  body: string;
  status: string;
  lastEditedBy: string;
  updatedAt: string;
};

function askAgent(message: string, caseId: string) {
  sendToAgentChat({
    message,
    context: JSON.stringify({ caseId }),
    submit: true,
    openSidebar: true,
  });
}

export default function CaseDesk() {
  const { caseId = "" } = useParams();
  const { data, isPending, error } = useActionQuery("get-case", { caseId });
  const [closing, setClosing] = useState(false);
  const [closingNote, setClosingNote] = useState("");

  const close = useActionMutation("close-case", {
    onSuccess: () => {
      setClosing(false);
      toast.success("Case closed");
    },
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not close"),
  });

  if (isPending) {
    return (
      <div className="grid gap-4 p-4 sm:p-6 lg:grid-cols-2">
        <Skeleton className="h-40 rounded-xl lg:col-span-2" />
        <Skeleton className="h-96 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Case not found.{" "}
        <Link className="underline" to="/cases">
          Back to cases
        </Link>
      </div>
    );
  }

  const c = data.case;
  const open = c.status === "open";
  const waiting = data.steps.filter((s) => s.status === "proposed").length;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 p-4 sm:p-6">
      <Link
        to="/cases"
        className="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <IconChevronLeft className="size-4" /> Cases
      </Link>

      <section className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "rounded-full border px-2 py-0.5 text-xs font-medium",
              SEVERITY_CLASS[c.severity],
            )}
          >
            {c.severity}
          </span>
          <h1 className="text-lg font-semibold tracking-tight">
            {RISK_LABEL[c.riskType] ?? c.riskType} · {c.childAlias} on {c.app}
          </h1>
          <span className="text-sm text-muted-foreground">
            {when(c.detectedAt)}
          </span>
          {open ? (
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              disabled={waiting > 0}
              title={waiting > 0 ? "Review every step first" : undefined}
              onClick={() => setClosing(true)}
            >
              Close case
            </Button>
          ) : (
            <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs">
              Closed
            </span>
          )}
        </div>
        <blockquote className="mt-4 rounded-xl border-l-4 border-indigo-400 bg-indigo-500/5 px-4 py-3 font-mono text-[15px]">
          “{c.flaggedPhrase}”
        </blockquote>
        <p className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
          <IconShieldLock className="mt-0.5 size-4 shrink-0 text-indigo-500" />
          Night Guard shared only this phrase. The rest of the chat stays on{" "}
          {c.childAlias}'s computer, and neither you nor the agent can see it.
        </p>
        {c.closingNote ? (
          <p className="mt-3 text-sm">
            <strong>Closing note:</strong> {c.closingNote}
          </p>
        ) : null}
        {open ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={() =>
                askAgent(
                  "Read this case and propose a calm plan of 3 to 6 steps for me to review.",
                  c.id,
                )
              }
            >
              <IconSparkles className="size-4" /> Ask the agent for a plan
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                askAgent(
                  "Draft the talk script I can use to open the conversation without blame.",
                  c.id,
                )
              }
            >
              Draft the talk script
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                askAgent(
                  "Draft the report text I can paste into the official report form.",
                  c.id,
                )
              }
            >
              Draft the report
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                askAgent(
                  "Write the case summary from the case log so far.",
                  c.id,
                )
              }
            >
              Write the case summary
            </Button>
          </div>
        ) : null}
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <section className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Plan
            {waiting > 0 ? (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] normal-case tracking-normal text-amber-800 dark:text-amber-300">
                {waiting} waiting for you
              </span>
            ) : null}
          </h2>
          <Guidance guidance={data.guidance} />
          {data.steps.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">
              No plan yet. Ask the agent, or add your own step below.
            </div>
          ) : (
            data.steps.map((step) => (
              <StepCard key={step.id} caseId={c.id} step={step} open={open} />
            ))
          )}
          {open ? <AddStep caseId={c.id} /> : null}
        </section>

        <section className="flex flex-col gap-4">
          <DraftTabs
            caseId={c.id}
            drafts={data.drafts}
            open={open}
          />
          <CaseLog events={data.events} />
        </section>
      </div>

      <AlertDialog open={closing} onOpenChange={setClosing}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Close this case?</AlertDialogTitle>
            <AlertDialogDescription>
              Write how it ended and any follow-up date. The log keeps
              everything.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea
            value={closingNote}
            onChange={(e) => setClosingNote(e.target.value)}
            placeholder="Talked with Lia, report filed, check in again next Sunday."
            maxLength={600}
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Keep open</AlertDialogCancel>
            <AlertDialogAction
              disabled={!closingNote.trim() || close.isPending}
              onClick={(e) => {
                e.preventDefault();
                close.mutate({ caseId: c.id, closingNote: closingNote.trim() });
              }}
            >
              Close case
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function Guidance({
  guidance,
}: {
  guidance: { stepKinds: string[]; reportTo: string[]; notes: string };
}) {
  return (
    <details className="group rounded-xl border border-indigo-400/25 bg-indigo-500/5 px-4 py-3 text-sm">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-1.5 text-muted-foreground">
        <span className="mr-1 font-medium text-foreground">
          A good plan here covers
        </span>
        {guidance.stepKinds.map((kind) => {
          const k = STEP_KIND[kind as keyof typeof STEP_KIND];
          return k ? (
            <span
              key={kind}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-xs"
            >
              <k.Icon className="size-3.5 text-indigo-500" />
              {k.label}
            </span>
          ) : null;
        })}
        <span className="ml-auto text-xs group-open:hidden">Why?</span>
      </summary>
      <p className="mt-3 text-muted-foreground">{guidance.notes}</p>
      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-muted-foreground">
        {guidance.reportTo.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </details>
  );
}

function StepCard({
  caseId,
  step,
  open,
}: {
  caseId: string;
  step: Step;
  open: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(step.title);
  const [detail, setDetail] = useState(step.detail);
  useEffect(() => {
    if (!editing) {
      setTitle(step.title);
      setDetail(step.detail);
    }
  }, [step.title, step.detail, editing]);

  const review = useActionMutation("review-step", {
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not update"),
  });
  const update = useActionMutation("update-step", {
    onSuccess: () => setEditing(false),
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not save"),
  });
  const kind = STEP_KIND[step.kind as keyof typeof STEP_KIND] ?? STEP_KIND.talk;
  const status = stepStatus(step.status);
  const decide = (decision: "approve" | "skip" | "done" | "reopen") =>
    review.mutate({ caseId, stepId: step.id, decision });

  return (
    <article
      className={cn(
        "rounded-xl border bg-card p-4",
        step.status === "proposed"
          ? "border-amber-400/60 shadow-[0_0_0_3px_rgba(245,158,11,0.08)]"
          : "border-border",
        (step.status === "done" || step.status === "skipped") && "opacity-70",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <kind.Icon className="size-4 text-indigo-500" />
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {kind.label}
        </span>
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-[11px] font-medium",
            status.className,
          )}
        >
          {status.label}
        </span>
        <span className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground">
          {step.proposedBy === "agent" ? (
            <IconRobot className="size-3.5" />
          ) : (
            <IconUser className="size-3.5" />
          )}
          {step.proposedBy === "agent" ? "Proposed by agent" : "Added by you"}
          {step.editedBy
            ? ` · edited by ${step.editedBy === "agent" ? "agent" : "you"}`
            : ""}
        </span>
      </div>
      {editing ? (
        <div className="mt-3 flex flex-col gap-2">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
          <Textarea
            value={detail}
            onChange={(e) => setDetail(e.target.value)}
            rows={5}
            maxLength={1200}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={update.isPending || !title.trim() || !detail.trim()}
              onClick={() =>
                update.mutate({ caseId, stepId: step.id, title: title.trim(), detail: detail.trim() })
              }
            >
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <h3 className="mt-2 font-medium">{step.title}</h3>
          <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
            {step.detail}
          </p>
        </>
      )}
      {open && !editing ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {step.status === "proposed" ? (
            <>
              <Button size="sm" disabled={review.isPending} onClick={() => decide("approve")}>
                <IconCheck className="size-4" /> Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                <IconPencil className="size-4" /> Edit
              </Button>
              <Button size="sm" variant="ghost" disabled={review.isPending} onClick={() => decide("skip")}>
                <IconX className="size-4" /> Skip
              </Button>
            </>
          ) : null}
          {step.status === "approved" ? (
            <>
              <Button size="sm" disabled={review.isPending} onClick={() => decide("done")}>
                <IconCheck className="size-4" /> Mark done
              </Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                <IconPencil className="size-4" /> Edit
              </Button>
            </>
          ) : null}
          {step.status === "done" || step.status === "skipped" ? (
            <Button size="sm" variant="ghost" disabled={review.isPending} onClick={() => decide("reopen")}>
              <IconArrowBackUp className="size-4" /> Reopen
            </Button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function AddStep({ caseId }: { caseId: string }) {
  const [title, setTitle] = useState("");
  const add = useActionMutation("add-plan-steps", {
    onSuccess: () => setTitle(""),
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not add"),
  });
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!title.trim()) return;
        add.mutate({
          caseId,
          steps: [{ kind: "follow_up", title: title.trim(), detail: "Added by the parent." }],
        });
      }}
    >
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Add your own step"
        maxLength={120}
      />
      <Button type="submit" variant="outline" disabled={!title.trim() || add.isPending}>
        <IconPlus className="size-4" /> Add
      </Button>
    </form>
  );
}

function DraftTabs({
  caseId,
  drafts,
  open,
}: {
  caseId: string;
  drafts: Draft[];
  open: boolean;
}) {
  const kinds = ["talk_script", "report_text", "case_summary"] as const;
  return (
    <Tabs defaultValue="talk_script" className="rounded-xl border border-border bg-card p-3">
      <TabsList className="w-full">
        {kinds.map((k) => {
          const d = drafts.find((x) => x.kind === k);
          return (
            <TabsTrigger key={k} value={k} className="flex-1 gap-1.5">
              {DRAFT_LABEL[k]}
              {d ? (
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    d.status === "approved" ? "bg-emerald-500" : "bg-amber-500",
                  )}
                />
              ) : null}
            </TabsTrigger>
          );
        })}
      </TabsList>
      {kinds.map((k) => (
        <TabsContent key={k} value={k}>
          <DraftEditor
            caseId={caseId}
            kind={k}
            draft={drafts.find((x) => x.kind === k)}
            open={open}
          />
        </TabsContent>
      ))}
    </Tabs>
  );
}

function DraftEditor({
  caseId,
  kind,
  draft,
  open,
}: {
  caseId: string;
  kind: "talk_script" | "report_text" | "case_summary";
  draft?: Draft | undefined;
  open: boolean;
}) {
  const [body, setBody] = useState(draft?.body ?? "");
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    if (!dirty) setBody(draft?.body ?? "");
  }, [draft?.body, dirty]);
  const save = useActionMutation("save-draft", {
    onSuccess: () => setDirty(false),
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not save"),
  });
  const approve = useActionMutation("approve-draft", {
    onError: (e) => toast.error(actionErrorMessage(e) ?? "Could not approve"),
  });

  if (!draft && !dirty) {
    return (
      <div className="flex flex-col items-start gap-3 p-3 text-sm text-muted-foreground">
        No {(DRAFT_LABEL[kind] ?? "draft").toLowerCase()} yet.
        {open ? (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                askAgent(`Draft the ${(DRAFT_LABEL[kind] ?? "draft").toLowerCase()} for this case.`, caseId)
              }
            >
              <IconSparkles className="size-4" /> Ask the agent
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setDirty(true)}>
              Write it myself
            </Button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 pt-1">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {draft ? (
          <>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 font-medium",
                draft.status === "approved"
                  ? STEP_STATUS.approved.className
                  : STEP_STATUS.proposed.className,
              )}
            >
              {draft.status === "approved" ? "Approved" : "Waiting for you"}
            </span>
            {draft.lastEditedBy === "agent" ? "Written by agent" : "Edited by you"} ·{" "}
            {when(draft.updatedAt)}
          </>
        ) : (
          "New draft"
        )}
        <Button
          size="icon"
          variant="ghost"
          className="ml-auto size-7"
          aria-label="Copy"
          onClick={() => {
            void navigator.clipboard?.writeText(body);
            toast.success("Copied");
          }}
        >
          <IconCopy className="size-4" />
        </Button>
      </div>
      <Textarea
        value={body}
        readOnly={!open}
        onChange={(e) => {
          setBody(e.target.value);
          setDirty(true);
        }}
        rows={12}
        className="font-[inherit] text-sm leading-relaxed"
      />
      {open ? (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!dirty || !body.trim() || save.isPending}
            onClick={() => save.mutate({ caseId, kind, body })}
          >
            Save my edits
          </Button>
          <Button
            size="sm"
            disabled={!draft || dirty || draft.status === "approved" || approve.isPending}
            onClick={() => approve.mutate({ caseId, kind })}
          >
            <IconCheck className="size-4" /> Approve
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function CaseLog({
  events,
}: {
  events: { id: string; actor: string; message: string; createdAt: string }[];
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Case log
      </h2>
      <ol className="flex flex-col gap-3">
        {events.map((e) => {
          const Icon =
            e.actor === "agent"
              ? IconRobot
              : e.actor === "night_guard"
                ? IconMoonStars
                : IconUser;
          return (
            <li key={e.id} className="flex gap-2.5 text-sm">
              <Icon
                className={cn(
                  "mt-0.5 size-4 shrink-0",
                  e.actor === "night_guard" ? "text-indigo-500" : "text-muted-foreground",
                )}
              />
              <div className="min-w-0">
                <p>{e.message}</p>
                <time className="text-xs text-muted-foreground">{when(e.createdAt)}</time>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
