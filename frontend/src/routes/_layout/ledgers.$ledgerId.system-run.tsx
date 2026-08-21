import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Play,
  RefreshCw,
  XCircle,
} from "lucide-react"
import { useEffect, useState } from "react"

import {
  ApiError,
  type LegacyImportJobPublic,
  LegacyImportService,
  ObligationsService,
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
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/ledgers/$ledgerId/system-run")({
  component: SystemRun,
  head: () => ({ meta: [{ title: "System Run - Findog Ledger" }] }),
})

const activeStatuses = new Set(["pending", "running"])

function formatDateTime(value: string | null) {
  if (value === null) return "—"
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value))
}

function currentPeriodValue() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

function parsePeriod(value: string) {
  const [year, month] = value.split("-").map(Number)
  if (
    !Number.isInteger(year) ||
    year < 1 ||
    year > 9999 ||
    !Number.isInteger(month) ||
    month < 1 ||
    month > 12
  ) {
    return null
  }
  return { year, month }
}

function statusDetails(job: LegacyImportJobPublic | null) {
  if (job === null) {
    return {
      label: "No run yet",
      icon: Clock3,
      className:
        "border-slate-500/30 bg-slate-500/15 text-slate-700 dark:text-slate-300",
    }
  }
  if (job.status === "succeeded") {
    return {
      label: "Completed",
      icon: CheckCircle2,
      className:
        "border-emerald-500/30 bg-emerald-500/15 text-emerald-800 dark:text-emerald-300",
    }
  }
  if (job.status === "failed") {
    return {
      label: "Failed",
      icon: XCircle,
      className:
        "border-red-500/30 bg-red-500/15 text-red-800 dark:text-red-300",
    }
  }
  return {
    label: job.status === "pending" ? "Queued" : "Running",
    icon: RefreshCw,
    className: "border-sky-500/30 bg-sky-500/15 text-sky-800 dark:text-sky-300",
  }
}

function SystemRun() {
  const { ledgerId } = Route.useParams()
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [confirmationOpen, setConfirmationOpen] = useState(false)
  const [ensurePeriod, setEnsurePeriod] = useState(currentPeriodValue)
  const [lastEnsureCount, setLastEnsureCount] = useState<number | null>(null)
  const jobQuery = useQuery({
    queryKey: ["legacy-import-job", ledgerId],
    queryFn: async (): Promise<LegacyImportJobPublic | null> => {
      try {
        return await LegacyImportService.readLegacyImportJob({ ledgerId })
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    refetchInterval: (query) =>
      activeStatuses.has(query.state.data?.status ?? "") ? 1_000 : false,
  })
  const startMutation = useMutation({
    mutationFn: () => LegacyImportService.startLegacyImport({ ledgerId }),
    onError: handleError.bind(showErrorToast),
    onSuccess: (job) => {
      queryClient.setQueryData(["legacy-import-job", ledgerId], job)
      setConfirmationOpen(false)
      showSuccessToast("Legacy import started")
    },
  })
  const ensureMutation = useMutation({
    mutationFn: (period: { year: number; month: number }) =>
      ObligationsService.ensureObligations({ ledgerId, ...period }),
    onError: handleError.bind(showErrorToast),
    onSuccess: (result) => {
      setLastEnsureCount(result.created_count)
      showSuccessToast(`Created ${result.created_count} obligations`)
      void queryClient.invalidateQueries({
        queryKey: ["obligations", ledgerId],
      })
    },
  })
  const job = jobQuery.data ?? null
  const status = statusDetails(job)
  const isActive = job !== null && activeStatuses.has(job.status)
  const selectedEnsurePeriod = parsePeriod(ensurePeriod)
  const progress =
    job !== null && job.total_obligations > 0
      ? Math.round((job.processed_obligations / job.total_obligations) * 100)
      : 0

  useEffect(() => {
    if (job?.status !== "succeeded") return
    void queryClient.invalidateQueries({ queryKey: ["obligations", ledgerId] })
    void queryClient.invalidateQueries({
      queryKey: ["category-groups", ledgerId],
    })
    void queryClient.invalidateQueries({ queryKey: ["categories", ledgerId] })
  }, [job?.status, ledgerId, queryClient])

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
            <Badge variant="outline">Temporary manual run</Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">System Run</h1>
          <p className="mt-1 text-muted-foreground">
            Start and monitor the temporary legacy workbook import for this
            ledger.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ensure obligations</CardTitle>
          <CardDescription>
            Create missing recurring obligations for the selected period and the
            following one. Existing obligations are left unchanged.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="ensure-period">
              Billing period
            </label>
            <Input
              id="ensure-period"
              type="month"
              value={ensurePeriod}
              onChange={(event) => setEnsurePeriod(event.target.value)}
            />
          </div>
          <LoadingButton
            loading={ensureMutation.isPending}
            disabled={selectedEnsurePeriod === null || isActive}
            onClick={() => {
              if (selectedEnsurePeriod !== null) {
                ensureMutation.mutate(selectedEnsurePeriod)
              }
            }}
          >
            Ensure obligations
          </LoadingButton>
          {lastEnsureCount !== null && (
            <p className="text-sm text-muted-foreground">
              Last run created {lastEnsureCount} obligations.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Legacy workbook import</CardTitle>
          <CardDescription>
            Importing replaces obligations in every matched legacy category.
            This temporary manual control will later be performed automatically
            by System Run.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Dialog open={confirmationOpen} onOpenChange={setConfirmationOpen}>
            <DialogTrigger asChild>
              <Button disabled={isActive || startMutation.isPending}>
                <Play />
                Start legacy import
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Start legacy import?</DialogTitle>
                <DialogDescription>
                  Existing obligations in matched categories will be replaced
                  with data from the legacy workbook.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline" disabled={startMutation.isPending}>
                    Cancel
                  </Button>
                </DialogClose>
                <LoadingButton
                  loading={startMutation.isPending}
                  onClick={() => startMutation.mutate()}
                >
                  Start import
                </LoadingButton>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          {isActive && (
            <p className="text-sm text-muted-foreground">
              An import is already in progress. Status refreshes every second.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Latest import status
            <Badge variant="outline" className={status.className}>
              <status.icon className={isActive ? "animate-spin" : undefined} />
              {status.label}
            </Badge>
          </CardTitle>
          <CardDescription>
            The most recent import job for this ledger.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {jobQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading status…</p>
          ) : jobQuery.isError ? (
            <Alert variant="destructive">
              <XCircle />
              <AlertTitle>Could not load import status</AlertTitle>
              <AlertDescription>
                Refresh the page or try again shortly.
              </AlertDescription>
            </Alert>
          ) : job === null ? (
            <p className="text-sm text-muted-foreground">
              No legacy import has been started for this ledger.
            </p>
          ) : (
            <>
              <div className="space-y-2">
                <div className="flex justify-between gap-4 text-sm">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">
                    {job.processed_obligations} / {job.total_obligations}
                  </span>
                </div>
                <div
                  className="h-2 overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={Math.max(job.total_obligations, 1)}
                  aria-valuenow={job.processed_obligations}
                  aria-label="Legacy import progress"
                >
                  <div
                    className="h-full bg-primary transition-[width]"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">Started</dt>
                  <dd>{formatDateTime(job.started_at)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Finished</dt>
                  <dd>{formatDateTime(job.finished_at)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">
                    Imported obligations
                  </dt>
                  <dd>{job.imported_obligations ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Replaced categories</dt>
                  <dd>{job.replaced_categories ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Created groups</dt>
                  <dd>{job.created_category_groups ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Created categories</dt>
                  <dd>{job.created_categories ?? "—"}</dd>
                </div>
              </dl>

              {job.error !== null && (
                <Alert variant="destructive">
                  <XCircle />
                  <AlertTitle>Import failed</AlertTitle>
                  <AlertDescription>{job.error}</AlertDescription>
                </Alert>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
