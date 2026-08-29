import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertCircle, ArrowRight, BarChart3, CircleAlert } from "lucide-react"
import { useMemo, useState } from "react"

import { AnalyticsService } from "@/client"
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
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

type Period = { year: number; month: number }

function currentPeriod(): Period {
  const now = new Date()
  return { year: now.getFullYear(), month: now.getMonth() + 1 }
}

function periodValue({ year, month }: Period) {
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`
}

function parsePeriod(value: string): Period | null {
  const [year, month] = value.split("-").map(Number)
  if (
    !Number.isInteger(year) ||
    !Number.isInteger(month) ||
    month < 1 ||
    month > 12
  ) {
    return null
  }
  return { year, month }
}

function addMonths(period: Period, offset: number): Period {
  const monthIndex = period.year * 12 + period.month - 1 + offset
  return { year: Math.floor(monthIndex / 12), month: (monthIndex % 12) + 1 }
}

function periodLabel(period: Period) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    year: "numeric",
  }).format(new Date(period.year, period.month - 1, 1))
}

function formatAmount(amount: string, currency: string | null) {
  return `${Number(amount).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}${currency ? ` ${currency}` : ""}`
}

function formatPercentage(value: string | null) {
  if (value === null) return "—"
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })
}

function obligationsHref(ledgerId: string, period: Period) {
  return `/ledgers/${ledgerId}?year=${period.year}&month=${period.month}`
}

function QueryState({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertTitle>Analytics are unavailable</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  )
}

export function AnalyticsDashboard({ ledgerId }: { ledgerId: string }) {
  const [selectedPeriod, setSelectedPeriod] = useState(currentPeriod)
  const rangeStart = useMemo(
    () => addMonths(selectedPeriod, -5),
    [selectedPeriod],
  )
  const summary = useQuery({
    queryFn: () =>
      AnalyticsService.readPeriodPaymentSummary({
        ledgerId,
        year: selectedPeriod.year,
        month: selectedPeriod.month,
      }),
    queryKey: ["analytics", "period-summary", ledgerId, selectedPeriod],
  })
  const totals = useQuery({
    queryFn: () =>
      AnalyticsService.readObligationPeriodTotals({
        ledgerId,
        _from: periodValue(rangeStart),
        to: periodValue(selectedPeriod),
      }),
    queryKey: [
      "analytics",
      "period-totals",
      ledgerId,
      rangeStart,
      selectedPeriod,
    ],
  })
  const cashflow = useQuery({
    queryFn: () =>
      AnalyticsService.readRemainingPeriodCashflow({
        ledgerId,
        year: selectedPeriod.year,
        month: selectedPeriod.month,
      }),
    queryKey: ["analytics", "cashflow", ledgerId, selectedPeriod],
  })

  const incomplete =
    (summary.data !== undefined && !summary.data.is_complete) ||
    (cashflow.data !== undefined && !cashflow.data.is_complete) ||
    totals.data?.points.some((point) => !point.is_complete) === true

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <BarChart3 className="size-5 text-primary" />
            <Badge variant="outline">Dashboard</Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-muted-foreground">
            Review payment progress, upcoming cashflow, and period totals.
          </p>
        </div>
        <label
          htmlFor="analytics-period"
          className="grid gap-1 text-sm font-medium"
        >
          Selected period
          <Input
            id="analytics-period"
            type="month"
            value={periodValue(selectedPeriod)}
            onChange={(event) => {
              const period = parsePeriod(event.target.value)
              if (period) setSelectedPeriod(period)
            }}
          />
        </label>
      </div>

      {incomplete && (
        <Alert>
          <CircleAlert />
          <AlertTitle>Some amounts are still unknown</AlertTitle>
          <AlertDescription>
            Totals only include confirmed known amounts. Check the incomplete
            indicators before treating a value as final.
          </AlertDescription>
        </Alert>
      )}

      <section className="grid gap-4 md:grid-cols-2">
        <PaymentProgressCard
          data={summary.data}
          isError={summary.isError}
          isLoading={summary.isLoading}
          ledgerId={ledgerId}
          period={selectedPeriod}
        />
        <Card>
          <CardHeader>
            <CardTitle>Explore categories</CardTitle>
            <CardDescription>
              Open a category to view its historical amount trend.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" variant="outline" asChild>
              <Link to="/ledgers/$ledgerId/categories" params={{ ledgerId }}>
                View category history
                <ArrowRight />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <CashflowChart
        data={cashflow.data}
        isError={cashflow.isError}
        isLoading={cashflow.isLoading}
        ledgerId={ledgerId}
        period={selectedPeriod}
      />

      <PeriodTotalsCard
        data={totals.data}
        isError={totals.isError}
        isLoading={totals.isLoading}
        ledgerId={ledgerId}
      />
    </div>
  )
}

function PaymentProgressCard({
  data,
  isError,
  isLoading,
  ledgerId,
  period,
}: {
  data:
    | Awaited<ReturnType<typeof AnalyticsService.readPeriodPaymentSummary>>
    | undefined
  isError: boolean
  isLoading: boolean
  ledgerId: string
  period: Period
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Payment progress</CardTitle>
        <CardDescription>{periodLabel(period)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : isError || !data ? (
          <QueryState message="Payment progress could not be loaded." />
        ) : (
          <>
            <p className="text-3xl font-bold">
              {formatPercentage(data.paid_percentage)}
              {data.paid_percentage !== null && "%"}
            </p>
            <div
              aria-label="Payment progress"
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={
                data.paid_percentage === null
                  ? undefined
                  : Number(data.paid_percentage)
              }
              className="h-2 overflow-hidden rounded-full bg-muted"
              role="progressbar"
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{
                  width: `${Math.min(Math.max(Number(data.paid_percentage ?? 0), 0), 100)}%`,
                }}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {data.paid_obligation_count} of {data.total_obligation_count}{" "}
              obligations paid
            </p>
            {!data.is_complete && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {data.unknown_amount_count} amount
                {data.unknown_amount_count === 1 ? "" : "s"} unknown
              </p>
            )}
            <Button className="w-full" variant="outline" size="sm" asChild>
              <a href={obligationsHref(ledgerId, period)}>
                View obligations
                <ArrowRight />
              </a>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function CashflowChart({
  data,
  isError,
  isLoading,
  ledgerId,
  period,
}: {
  data:
    | Awaited<ReturnType<typeof AnalyticsService.readRemainingPeriodCashflow>>
    | undefined
  isError: boolean
  isLoading: boolean
  ledgerId: string
  period: Period
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Remaining cashflow</CardTitle>
        <CardDescription>
          Cumulative scheduled unpaid amounts in {periodLabel(period)}. Each
          currency is shown separately.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : isError || !data ? (
          <QueryState message="Cashflow could not be loaded." />
        ) : data.currency_summaries.length === 0 ? (
          <>
            <p className="text-sm text-muted-foreground">
              No unpaid known amounts.
            </p>
            {!data.is_complete && (
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {data.unknown_amount_count} amount
                {data.unknown_amount_count === 1 ? " is" : "s are"} unknown.
              </p>
            )}
          </>
        ) : (
          <div className="grid gap-6 lg:grid-cols-2">
            {data.currency_summaries.map((summary) => (
              <CashflowCurrencyChart
                key={summary.currency}
                ledgerId={ledgerId}
                period={period}
                summary={summary}
              />
            ))}
            {!data.is_complete && (
              <p className="text-sm text-amber-700 dark:text-amber-300 lg:col-span-2">
                {data.unknown_amount_count} unknown and{" "}
                {data.without_due_date_count} unscheduled
              </p>
            )}
            <Button
              className="w-full lg:col-span-2"
              variant="outline"
              size="sm"
              asChild
            >
              <a href={obligationsHref(ledgerId, period)}>
                Review unpaid obligations
                <ArrowRight />
              </a>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CashflowCurrencyChart({
  ledgerId,
  period,
  summary,
}: {
  ledgerId: string
  period: Period
  summary: Awaited<
    ReturnType<typeof AnalyticsService.readRemainingPeriodCashflow>
  >["currency_summaries"][number]
}) {
  const maximum = Math.max(
    ...summary.daily.map((point) => Number(point.cumulative_amount)),
    1,
  )
  const points = summary.daily
    .map((point, index) => {
      const x =
        summary.daily.length === 1
          ? 50
          : (index / (summary.daily.length - 1)) * 100
      const y = 100 - (Number(point.cumulative_amount) / maximum) * 100
      return `${x},${y}`
    })
    .join(" ")

  return (
    <section className="rounded-lg border p-4">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h3 className="font-semibold">{summary.currency ?? "No currency"}</h3>
        <strong>
          {formatAmount(summary.total_known_amount, summary.currency)}
        </strong>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-muted-foreground">Scheduled</p>
          <p className="font-medium">
            {formatAmount(summary.scheduled_known_amount, summary.currency)}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Unscheduled</p>
          <p className="font-medium">
            {formatAmount(summary.unscheduled_known_amount, summary.currency)}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Overdue</p>
          <p className="font-medium text-destructive">
            {formatAmount(summary.overdue_known_amount, summary.currency)}
          </p>
        </div>
      </div>
      {summary.daily.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          No scheduled payments in this period.
        </p>
      ) : (
        <div className="mt-6">
          <svg
            aria-label={`Cumulative cashflow for ${summary.currency ?? "no currency"}`}
            className="h-52 w-full overflow-visible"
            preserveAspectRatio="none"
            role="img"
            viewBox="0 0 100 100"
          >
            <line
              className="stroke-border"
              strokeWidth="0.5"
              x1="0"
              x2="100"
              y1="100"
              y2="100"
            />
            <polyline
              className="fill-none stroke-primary"
              points={points}
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
            {summary.daily.map((point, index) => {
              const x =
                summary.daily.length === 1
                  ? 50
                  : (index / (summary.daily.length - 1)) * 100
              const y = 100 - (Number(point.cumulative_amount) / maximum) * 100
              return (
                <circle
                  className={
                    point.is_overdue ? "fill-destructive" : "fill-primary"
                  }
                  cx={x}
                  cy={y}
                  key={point.due_date}
                  r="2.5"
                >
                  <title>
                    {point.due_date}:{" "}
                    {formatAmount(point.cumulative_amount, summary.currency)}
                  </title>
                </circle>
              )
            })}
          </svg>
          <div className="mt-2 flex justify-between text-xs text-muted-foreground">
            <span>{summary.daily[0]?.due_date}</span>
            <span>{summary.daily[summary.daily.length - 1]?.due_date}</span>
          </div>
        </div>
      )}
      <Button className="mt-4 w-full" size="sm" variant="ghost" asChild>
        <a href={obligationsHref(ledgerId, period)}>
          View contributing obligations
        </a>
      </Button>
    </section>
  )
}

function PeriodTotalsCard({
  data,
  isError,
  isLoading,
  ledgerId,
}: {
  data:
    | Awaited<ReturnType<typeof AnalyticsService.readObligationPeriodTotals>>
    | undefined
  isError: boolean
  isLoading: boolean
  ledgerId: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Obligation totals by period</CardTitle>
        <CardDescription>
          Last six periods. Each currency is shown separately and is never
          combined.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-56 w-full" />
        ) : isError || !data ? (
          <QueryState message="Period totals could not be loaded." />
        ) : data.points.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No periods to display.
          </p>
        ) : !data.points.some(
            (point) => point.currency_summaries.length > 0,
          ) ? (
          <p className="text-sm text-muted-foreground">
            No known obligation amounts in this range.
          </p>
        ) : (
          <div className="space-y-8 overflow-x-auto pb-2">
            {Array.from(
              new Set(
                data.points.flatMap((point) =>
                  point.currency_summaries.map(
                    (summary) => summary.currency ?? "No currency",
                  ),
                ),
              ),
            ).map((currency) => {
              const amounts = data.points.map((point) => {
                const summary = point.currency_summaries.find(
                  (item) => (item.currency ?? "No currency") === currency,
                )
                return Number(summary?.total_known_amount ?? 0)
              })
              const maximum = Math.max(...amounts, 1)
              return (
                <div className="min-w-150" key={currency}>
                  <h3 className="mb-3 text-sm font-medium">{currency}</h3>
                  <div className="flex h-56 items-end gap-3 border-b border-l px-3 pt-4">
                    {data.points.map((point, index) => (
                      <a
                        key={periodValue(point.period)}
                        href={obligationsHref(ledgerId, point.period)}
                        className="group flex h-full min-w-16 flex-1 flex-col"
                        aria-label={`View obligations for ${periodLabel(point.period)}`}
                      >
                        <div className="relative flex min-h-0 flex-1 flex-col justify-end">
                          <span className="absolute -top-5 inset-x-0 text-center text-xs font-medium opacity-0 transition-opacity group-hover:opacity-100">
                            {formatAmount(
                              String(amounts[index]),
                              currency === "No currency" ? null : currency,
                            )}
                          </span>
                          <span
                            className="min-h-1 rounded-t bg-primary/80 transition-colors group-hover:bg-primary"
                            style={{
                              height: `${Math.max((amounts[index] / maximum) * 100, 1)}%`,
                            }}
                          />
                        </div>
                        <span className="mt-2 text-center text-xs text-muted-foreground">
                          {periodLabel(point.period)}
                        </span>
                        {!point.is_complete && (
                          <span className="text-center text-xs text-amber-700 dark:text-amber-300">
                            incomplete
                          </span>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
