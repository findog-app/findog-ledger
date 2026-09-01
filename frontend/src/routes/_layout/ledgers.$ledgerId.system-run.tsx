import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { AlertCircle, ArrowLeft, Play, XCircle } from "lucide-react"
import { useState } from "react"

import {
  type SystemRunPublic,
  type SystemRunStepPublic,
  SystemRunsService,
} from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/ledgers/$ledgerId/system-run")({
  component: SystemRun,
  head: () => ({ meta: [{ title: "System Run - Findog Ledger" }] }),
})

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value))
}

function statusVariant(status: SystemRunPublic["status"]) {
  if (status === "success") return "default"
  if (status === "running") return "secondary"
  return "destructive"
}

function formatDuration(startedAt: string, finishedAt: string | null) {
  if (!finishedAt) return null

  const milliseconds =
    new Date(finishedAt).getTime() - new Date(startedAt).getTime()
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return null

  if (milliseconds < 1_000) return `${milliseconds} ms`

  const seconds = Math.floor(milliseconds / 1_000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return minutes > 0
    ? `${minutes}m ${remainingSeconds}s`
    : `${remainingSeconds}s`
}

function formatSummaryKey(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/^./, (character) => character.toUpperCase())
}

function formatSummaryValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number")
    return String(value)
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (value === null) return "None"
  return JSON.stringify(value)
}

const summaryLabels: Record<string, Record<string, string>> = {
  ensure_obligations: {
    created_obligations: "Created obligations",
  },
  scheduled_reports: {
    sent: "Reports sent",
    skipped: "Reports skipped",
    failed: "Reports failed",
  },
  legacy_import: {
    created_category_groups: "Created category groups",
    created_categories: "Created categories",
    replaced_categories: "Replaced categories",
    imported_obligations: "Imported obligations",
  },
}

function StepSummary({ step }: { step: SystemRunStepPublic }) {
  if (!step.summary || Object.keys(step.summary).length === 0) return null

  const labels = summaryLabels[step.task_name] ?? {}
  const entries = Object.entries(step.summary)
  const knownEntries = entries.filter(([key]) => labels[key])
  const additionalEntries = entries.filter(([key]) => !labels[key])

  return (
    <div className="space-y-2 text-sm">
      {knownEntries.length > 0 && (
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
          {knownEntries.map(([key, value]) => (
            <div className="flex justify-between gap-3" key={key}>
              <dt className="text-muted-foreground">{labels[key]}</dt>
              <dd className="font-medium">{formatSummaryValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {additionalEntries.length > 0 && (
        <details className="rounded-md border px-3 py-2">
          <summary className="cursor-pointer font-medium">
            {knownEntries.length > 0 ? "Additional details" : "Step details"}
          </summary>
          <dl className="mt-2 space-y-1">
            {additionalEntries.map(([key, value]) => (
              <div className="flex flex-wrap justify-between gap-x-3" key={key}>
                <dt className="text-muted-foreground">
                  {formatSummaryKey(key)}
                </dt>
                <dd className="break-all text-right">
                  {formatSummaryValue(value)}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  )
}

function SystemRun() {
  const { ledgerId } = Route.useParams()
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [confirmationOpen, setConfirmationOpen] = useState(false)
  const [manualTaskNames, setManualTaskNames] = useState<string[]>([])
  const tasks = useQuery({
    queryKey: ["system-run-tasks"],
    queryFn: () => SystemRunsService.readSystemRunTasks(),
  })
  const history = useQuery({
    queryKey: ["system-runs"],
    queryFn: () => SystemRunsService.readSystemRuns(),
    refetchInterval: (query) =>
      query.state.data?.data.some((run) => run.status === "running")
        ? 1_000
        : false,
  })
  const startRun = useMutation({
    mutationFn: () =>
      SystemRunsService.startSystemRun({
        requestBody:
          manualTaskNames.length > 0
            ? { manual_task_names: manualTaskNames }
            : undefined,
      }),
    onError: handleError.bind(showErrorToast),
    onSuccess: (run) => {
      queryClient.setQueryData(
        ["system-runs"],
        (previous: typeof history.data) =>
          previous
            ? { ...previous, data: [run, ...previous.data] }
            : { data: [run], count: 1 },
      )
      setConfirmationOpen(false)
      showSuccessToast(
        `System Run finished with ${run.status.replace(/_/g, " ")}`,
      )
    },
  })

  const toggleManualTask = (name: string, checked: boolean) => {
    setManualTaskNames((previous) =>
      checked ? [...previous, name] : previous.filter((task) => task !== name),
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="w-fit" asChild>
          <Link to="/ledgers/$ledgerId" params={{ ledgerId }}>
            <ArrowLeft />
            Back to workspace
          </Link>
        </Button>
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Play className="size-5 text-primary" />
            <Badge variant="outline">Administrator</Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">System Run</h1>
          <p className="mt-1 text-muted-foreground">
            Run scheduled maintenance tasks and inspect their history.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Start manual run</CardTitle>
          <CardDescription>
            Run all scheduled tasks, optionally selecting manual-only tasks.
            Disabled tasks cannot be started.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {tasks.isError ? (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertTitle>Could not load System Run tasks</AlertTitle>
              <AlertDescription>
                Only administrators can start a System Run.
              </AlertDescription>
            </Alert>
          ) : (
            <>
              {tasks.data && (
                <div className="space-y-3">
                  <p className="text-sm font-medium">Configured tasks</p>
                  {tasks.data.map((task) => (
                    <div className="flex items-center gap-2" key={task.name}>
                      {task.mode === "manual_only" ? (
                        <>
                          <Checkbox
                            id={`system-run-task-${task.name}`}
                            checked={manualTaskNames.includes(task.name)}
                            onCheckedChange={(checked) =>
                              toggleManualTask(task.name, checked === true)
                            }
                          />
                          <Label htmlFor={`system-run-task-${task.name}`}>
                            {task.name.replace(/_/g, " ")}
                          </Label>
                        </>
                      ) : (
                        <span className="text-sm">
                          {task.name.replace(/_/g, " ")}
                        </span>
                      )}
                      <Badge variant="outline" className="ml-auto">
                        {task.mode === "scheduled"
                          ? "included in run all"
                          : task.mode === "manual_only"
                            ? "select to include"
                            : "disabled"}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
              <Dialog
                open={confirmationOpen}
                onOpenChange={setConfirmationOpen}
              >
                <DialogTrigger asChild>
                  <Button disabled={tasks.isLoading || startRun.isPending}>
                    <Play /> Start System Run
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Start System Run?</DialogTitle>
                    <DialogDescription>
                      Scheduled tasks will run now. Manual-only tasks run only
                      when selected above.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <DialogClose asChild>
                      <Button variant="outline" disabled={startRun.isPending}>
                        Cancel
                      </Button>
                    </DialogClose>
                    <LoadingButton
                      loading={startRun.isPending}
                      onClick={() => startRun.mutate()}
                    >
                      Start run
                    </LoadingButton>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Run history</CardTitle>
          <CardDescription>
            Includes every task and ledger outcome, including skipped work.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {history.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading history…</p>
          ) : history.isError ? (
            <Alert variant="destructive">
              <XCircle />
              <AlertTitle>Could not load System Run history</AlertTitle>
              <AlertDescription>
                Refresh the page and try again.
              </AlertDescription>
            </Alert>
          ) : history.data?.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">No System Runs yet.</p>
          ) : (
            history.data?.data.map((run) => (
              <section className="rounded-lg border p-4" key={run.id}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {formatDateTime(run.effective_at)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {run.trigger} · {run.timezone} · {run.business_date}
                    </p>
                  </div>
                  <Badge variant={statusVariant(run.status)}>
                    {run.status.replace(/_/g, " ")}
                  </Badge>
                </div>
                {run.error && (
                  <p className="mt-3 text-sm text-destructive">{run.error}</p>
                )}
                {run.summary && (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {String(run.summary.succeeded_steps ?? 0)} succeeded ·{" "}
                    {String(run.summary.failed_steps ?? 0)} failed ·{" "}
                    {String(run.summary.skipped_steps ?? 0)} skipped
                  </p>
                )}
                <div className="mt-4 space-y-2">
                  {run.steps?.map((step) => {
                    const duration = formatDuration(
                      step.started_at,
                      step.finished_at,
                    )
                    return (
                      <div
                        className="rounded-md border p-3 text-sm"
                        key={step.id}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <span className="font-medium">
                            {step.task_name.replace(/_/g, " ")}
                            {step.ledger_id ? ` · ${step.ledger_id}` : ""}
                          </span>
                          <span className="text-muted-foreground">
                            {step.status}
                            {duration ? ` · ${duration}` : ""}
                          </span>
                        </div>
                        {step.skip_reason && (
                          <p className="mt-2 text-muted-foreground">
                            Skip reason: {step.skip_reason}
                          </p>
                        )}
                        {step.error && (
                          <p className="mt-2 text-destructive">{step.error}</p>
                        )}
                        {step.summary &&
                          Object.keys(step.summary).length > 0 && (
                            <div className="mt-2">
                              <StepSummary step={step} />
                            </div>
                          )}
                      </div>
                    )
                  })}
                </div>
              </section>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
