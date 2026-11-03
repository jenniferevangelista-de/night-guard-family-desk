import {
  actionErrorMessage,
  useActionMutation,
  useActionQuery,
} from "@agent-native/core/client/hooks";
import {
  IconChevronDown,
  IconMoonStars,
  IconShieldLock,
} from "@tabler/icons-react";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DEMO_ALERTS,
  LEAKY_ALERT,
  RISK_LABEL,
  SEVERITY_CLASS,
  when,
} from "@/lib/case-labels";
import { cn } from "@/lib/utils";

export default function CasesIndex() {
  const navigate = useNavigate();
  const { data, isPending } = useActionQuery("list-cases", {});
  const receive = useActionMutation("receive-alert", {
    onSuccess: (result) => {
      toast.success("New Night Guard alert");
      navigate(`/cases/${result.id}`);
    },
    onError: (error) =>
      toast.error(actionErrorMessage(error) ?? "The alert was refused."),
  });

  const cases = data?.cases ?? [];

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex max-w-xl items-start gap-3 rounded-xl border border-border bg-card p-3 text-sm">
          <IconShieldLock className="mt-0.5 size-5 shrink-0 text-indigo-500" />
          <p className="text-muted-foreground">
            Night Guard runs on your child's computer. It sends this desk only
            the risk, the app and one flagged phrase.{" "}
            <span className="text-foreground">
              The full chat never leaves their device.
            </span>
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button disabled={receive.isPending}>
              <IconMoonStars className="size-4" />
              Simulate an alert
              <IconChevronDown className="size-4 opacity-70" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuLabel>Fictional Night Guard alerts</DropdownMenuLabel>
            {DEMO_ALERTS.map((alert) => (
              <DropdownMenuItem
                key={alert.label}
                onSelect={() => receive.mutate({ ...alert.payload })}
              >
                {alert.label}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() =>
                receive.mutate(
                  LEAKY_ALERT as Parameters<typeof receive.mutate>[0],
                )
              }
            >
              Test: send the full chat (must be refused)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : cases.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No alerts. When Night Guard flags something, the case opens here and
          the agent helps you plan what to do.
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {cases.map((c) => (
            <li key={c.id}>
              <Link
                to={`/cases/${c.id}`}
                className={cn(
                  "flex flex-col gap-2 rounded-xl border border-border bg-card p-4 transition-colors hover:bg-accent/50",
                  c.status === "closed" && "opacity-60",
                )}
              >
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span
                    className={cn(
                      "rounded-full border px-2 py-0.5 text-xs font-medium",
                      SEVERITY_CLASS[c.severity],
                    )}
                  >
                    {c.severity}
                  </span>
                  <strong className="font-semibold">
                    {RISK_LABEL[c.riskType] ?? c.riskType}
                  </strong>
                  <span className="text-muted-foreground">
                    {c.childAlias} · {c.app} · {when(c.detectedAt)}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {c.status === "closed"
                      ? "Closed"
                      : c.stepsWaiting > 0
                        ? `${c.stepsWaiting} step(s) waiting for you`
                        : c.stepsTotal === 0
                          ? "No plan yet"
                          : `${c.stepsDone}/${c.stepsTotal} done`}
                  </span>
                </div>
                <p className="truncate font-mono text-sm text-foreground/80">
                  “{c.flaggedPhrase}”
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
