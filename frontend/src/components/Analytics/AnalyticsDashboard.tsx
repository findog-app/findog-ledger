import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AlertCircle, ArrowRight, BarChart3 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { AnalyticsService, CategoriesService } from "@/client"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"

type Period = { year: number; month: number }

function currentPeriod(): Period {
  const now = new Date()
  return { year: now.getFullYear(), month: now.getMonth() + 1 }
}

function periodValue({ year, month }: Period) {
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`
}

function addMonths(period: Period, offset: number): Period {
  const monthIndex = period.year * 12 + period.month - 1 + offset
  return { year: Math.floor(monthIndex / 12), month: (monthIndex % 12) + 1 }
}

function periodLabel(period: Period) {
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "numeric",
  }).format(new Date(period.year, period.month - 1, 1))
}

function formatAmount(amount: string, currency: string | null) {
  return `${Number(amount).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}${currency ? ` ${currency}` : ""}`
}

function formatPercentage(value: string | null) {
  if (value === null) return "—"
  return Number(value).toLocaleString("en-GB", {
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
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>()
  const selectablePeriods = useMemo(
    () =>
      Array.from({ length: 25 }, (_, index) =>
        addMonths(currentPeriod(), index - 12),
      ),
    [],
  )
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
  const categories = useQuery({
    queryFn: () => CategoriesService.readCategories({ ledgerId }),
    queryKey: ["categories", ledgerId],
  })

  useEffect(() => {
    const availableCategories = categories.data?.data
    if (!availableCategories?.length) return
    if (
      !availableCategories.some(
        (category) => category.id === selectedCategoryId,
      )
    ) {
      setSelectedCategoryId(availableCategories[0].id)
    }
  }, [categories.data, selectedCategoryId])

  const categoryHistory = useQuery({
    queryFn: () =>
      AnalyticsService.readCategoryAmountHistory({
        ledgerId,
        categoryId: selectedCategoryId!,
        _from: periodValue(rangeStart),
        to: periodValue(selectedPeriod),
      }),
    queryKey: [
      "analytics",
      "category-history",
      ledgerId,
      selectedCategoryId,
      rangeStart,
      selectedPeriod,
    ],
    enabled: Boolean(selectedCategoryId),
  })

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
            Review payment progress, the payment schedule, and period totals.
          </p>
          <Link
            className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            to="/ledgers/$ledgerId/categories"
            params={{ ledgerId }}
          >
            Explore category history <ArrowRight className="size-4" />
          </Link>
        </div>
        <div className="grid gap-1 text-sm font-medium">
          Selected period
          <Select
            value={periodValue(selectedPeriod)}
            onValueChange={(value) => {
              const period = selectablePeriods.find(
                (item) => periodValue(item) === value,
              )
              if (period) setSelectedPeriod(period)
            }}
          >
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {selectablePeriods.map((period) => (
                <SelectItem
                  key={periodValue(period)}
                  value={periodValue(period)}
                >
                  {periodLabel(period)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <PaymentProgressCard
          data={summary.data}
          isError={summary.isError}
          isLoading={summary.isLoading}
          ledgerId={ledgerId}
          period={selectedPeriod}
        />
        <CashflowOverviewCards
          data={cashflow.data}
          isError={cashflow.isError}
          isLoading={cashflow.isLoading}
        />
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

      <CategoryHistoryCard
        categories={categories.data}
        categoriesError={categories.isError}
        categoriesLoading={categories.isLoading}
        data={categoryHistory.data}
        isError={categoryHistory.isError}
        isLoading={categoryHistory.isLoading}
        selectedCategoryId={selectedCategoryId}
        setSelectedCategoryId={setSelectedCategoryId}
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
    <Card className="gap-3 py-4">
      <CardHeader className="gap-1">
        <CardTitle>Payment progress</CardTitle>
        <CardDescription>{periodLabel(period)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : isError || !data ? (
          <QueryState message="Payment progress could not be loaded." />
        ) : (
          <>
            <p className="text-[28px] font-bold">
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
            <Button className="mt-2 px-0" variant="link" size="sm" asChild>
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

function CashflowOverviewCards({
  data,
  isError,
  isLoading,
}: {
  data:
    | Awaited<ReturnType<typeof AnalyticsService.readRemainingPeriodCashflow>>
    | undefined
  isError: boolean
  isLoading: boolean
}) {
  if (isLoading) {
    return Array.from({ length: 3 }, (_, index) => (
      <Card className="gap-3 py-4" key={index}>
        <CardHeader className="gap-1">
          <Skeleton className="h-5 w-28" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    ))
  }

  if (isError || !data) {
    return (
      <Card className="gap-3 py-4 sm:col-span-2 xl:col-span-3">
        <CardContent className="pt-6">
          <QueryState message="Payment schedule could not be loaded." />
        </CardContent>
      </Card>
    )
  }

  const nextDueDate = data.currency_summaries
    .flatMap((summary) => summary.daily)
    .filter((point) => !point.is_overdue)
    .sort((a, b) => a.due_date.localeCompare(b.due_date))[0]?.due_date

  return (
    <>
      <CashflowMetricCard
        label="Remaining to pay"
        values={data.currency_summaries.map((summary) => ({
          amount: summary.total_known_amount,
          currency: summary.currency,
        }))}
        emptyLabel="0"
        emptyDescription="No known unpaid amounts"
      />
      <CashflowMetricCard
        label="Overdue"
        values={data.currency_summaries
          .filter((summary) => Number(summary.overdue_known_amount) > 0)
          .map((summary) => ({
            amount: summary.overdue_known_amount,
            currency: summary.currency,
          }))}
        emptyLabel="0"
        emptyDescription="No overdue obligations"
        tone={
          data.currency_summaries.some(
            (summary) => Number(summary.overdue_known_amount) > 0,
          )
            ? "destructive"
            : undefined
        }
      />
      <Card className="gap-3 py-4">
        <CardHeader className="gap-1">
          <CardDescription>Next payment due</CardDescription>
          <CardTitle className="text-[28px] font-bold">
            {nextDueDate ? formatDueDate(nextDueDate) : "0"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {nextDueDate
              ? "Earliest upcoming unpaid obligation."
              : "No scheduled payment"}
          </p>
        </CardContent>
      </Card>
    </>
  )
}

function CashflowMetricCard({
  label,
  values,
  emptyLabel,
  emptyDescription,
  tone,
}: {
  label: string
  values: { amount: string; currency: string | null }[]
  emptyLabel: string
  emptyDescription?: string
  tone?: "destructive"
}) {
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="gap-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle
          className={`text-[28px] font-bold ${tone === "destructive" && values.length > 0 ? "text-destructive" : ""}`}
        >
          {values.length === 0
            ? emptyLabel
            : values.map((value) => (
                <span className="block" key={value.currency ?? "none"}>
                  {formatAmount(value.amount, value.currency)}
                </span>
              ))}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {values.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            {values.length} currenc{values.length === 1 ? "y" : "ies"}
          </p>
        ) : emptyDescription ? (
          <p className="text-sm text-muted-foreground">{emptyDescription}</p>
        ) : null}
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
    <Card className="gap-4 py-5">
      <CardHeader>
        <CardTitle>Payment schedule</CardTitle>
        <CardDescription>
          Unpaid amounts grouped by due date in {periodLabel(period)}. Each
          currency is shown separately.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : isError || !data ? (
          <QueryState message="Cashflow could not be loaded." />
        ) : data.currency_summaries.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              No unpaid known amounts.
            </p>
            <ScheduleCompletenessStatus data={data} />
          </div>
        ) : (
          <div className="space-y-6">
            <ScheduleCompletenessStatus data={data} />
            <div className="grid gap-8 xl:grid-cols-2">
              {data.currency_summaries.map((summary) => (
                <div
                  className={
                    data.currency_summaries.length === 1
                      ? "xl:col-span-2"
                      : undefined
                  }
                  key={summary.currency}
                >
                  <CashflowCurrencyChart summary={summary} />
                </div>
              ))}
            </div>
            <Button className="px-0" variant="link" size="sm" asChild>
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

function ScheduleCompletenessStatus({
  data,
}: {
  data: Awaited<ReturnType<typeof AnalyticsService.readRemainingPeriodCashflow>>
}) {
  if (data.is_complete) return null

  return (
    <div className="flex flex-wrap gap-2">
      {data.unknown_amount_count > 0 && (
        <Badge
          variant="outline"
          className="border-amber-500 text-amber-700 dark:text-amber-300"
        >
          {data.unknown_amount_count} amount
          {data.unknown_amount_count === 1 ? "" : "s"} unknown
        </Badge>
      )}
      {data.without_due_date_count > 0 && (
        <Badge
          variant="outline"
          className="border-amber-500 text-amber-700 dark:text-amber-300"
        >
          {data.without_due_date_count} obligation
          {data.without_due_date_count === 1 ? "" : "s"} without a due date
        </Badge>
      )}
    </div>
  )
}

function CashflowCurrencyChart({
  summary,
}: {
  summary: Awaited<
    ReturnType<typeof AnalyticsService.readRemainingPeriodCashflow>
  >["currency_summaries"][number]
}) {
  const maximum = chartMaximum(
    summary.daily.map((point) => Number(point.amount)),
  )
  const chartHeight = 72
  const chartBottom = 84
  const chartLeft = 90
  const chartWidth = 380
  const tickValues = [maximum, maximum / 2, 0]
  const labelEvery = Math.max(1, Math.ceil(summary.daily.length / 5))

  return (
    <section>
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
          <p className="font-medium">
            <span
              className={
                Number(summary.overdue_known_amount) > 0
                  ? "text-destructive"
                  : "text-muted-foreground"
              }
            >
              {formatAmount(summary.overdue_known_amount, summary.currency)}
            </span>
          </p>
        </div>
      </div>
      {summary.daily.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          No scheduled payments in this period.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <svg
            aria-label={`Scheduled payments for ${summary.currency ?? "no currency"}`}
            className="h-56 min-w-150 w-full"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            viewBox="0 0 500 100"
          >
            <title>Scheduled unpaid amounts by due date</title>
            <desc>
              Bars show the amount due on each date. Hover a bar for its daily
              and cumulative amounts.
            </desc>
            {tickValues.map((value, index) => {
              const y = 12 + (index * chartHeight) / (tickValues.length - 1)
              return (
                <g key={value}>
                  <line
                    className="stroke-border"
                    strokeDasharray={
                      index === tickValues.length - 1 ? undefined : "2 2"
                    }
                    strokeWidth="0.5"
                    x1={chartLeft}
                    x2={chartLeft + chartWidth}
                    y1={y}
                    y2={y}
                  />
                  <text
                    className="fill-muted-foreground"
                    fontSize="6"
                    textAnchor="end"
                    x={chartLeft - 2}
                    y={y + 1.5}
                  >
                    {formatCompactAmount(value, summary.currency)}
                  </text>
                </g>
              )
            })}
            {summary.daily.map((point, index) => {
              const slotWidth = chartWidth / summary.daily.length
              const barWidth = Math.min(slotWidth * 0.62, 8)
              const x =
                chartLeft + slotWidth * index + (slotWidth - barWidth) / 2
              const height = (Number(point.amount) / maximum) * chartHeight
              const y = chartBottom - height
              const showLabel =
                index % labelEvery === 0 || index === summary.daily.length - 1
              return (
                <g key={point.due_date}>
                  <rect
                    className={
                      point.is_overdue ? "fill-destructive" : "fill-primary"
                    }
                    height={height}
                    rx="1"
                    width={barWidth}
                    x={x}
                    y={y}
                  >
                    <title>
                      {formatDueDate(point.due_date)}:{" "}
                      {formatAmount(point.amount, summary.currency)} due;{" "}
                      {formatAmount(point.cumulative_amount, summary.currency)}{" "}
                      cumulative
                    </title>
                  </rect>
                  {showLabel && (
                    <text
                      className="fill-muted-foreground"
                      fontSize="6"
                      textAnchor="middle"
                      x={x + barWidth / 2}
                      y="94"
                    >
                      {formatShortDueDate(point.due_date)}
                    </text>
                  )}
                </g>
              )
            })}
          </svg>
        </div>
      )}
    </section>
  )
}

function formatDueDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`))
}

function formatShortDueDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
  }).format(new Date(`${value}T00:00:00`))
}

function formatCompactAmount(amount: number, currency: string | null) {
  return `${amount.toLocaleString("en-GB", {
    maximumFractionDigits: 0,
    notation: "compact",
  })}${currency ? ` ${currency}` : ""}`
}

function CategoryHistoryCard({
  categories,
  categoriesError,
  categoriesLoading,
  data,
  isError,
  isLoading,
  selectedCategoryId,
  setSelectedCategoryId,
}: {
  categories:
    | Awaited<ReturnType<typeof CategoriesService.readCategories>>
    | undefined
  categoriesError: boolean
  categoriesLoading: boolean
  data:
    | Awaited<ReturnType<typeof AnalyticsService.readCategoryAmountHistory>>
    | undefined
  isError: boolean
  isLoading: boolean
  selectedCategoryId: string | undefined
  setSelectedCategoryId: (categoryId: string) => void
}) {
  const knownPoints =
    data?.points.filter((point) => point.state === "known") ?? []
  const amounts =
    data?.points.map((point) =>
      point.state === "known" ? Number(point.current_amount) : 0,
    ) ?? []
  const maximum = Math.max(...amounts, 1)
  const currency = knownPoints[0]?.currency ?? null

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex sm:flex-row sm:items-center sm:justify-between">
        <div>
          <CardTitle>Category amount history</CardTitle>
          <CardDescription>
            Last six periods. Missing and unknown amounts remain explicit.
          </CardDescription>
        </div>
        {categoriesLoading ? (
          <Skeleton className="h-9 w-48" />
        ) : categoriesError || !categories ? null : categories.data.length ===
          0 ? null : (
          <Select
            value={selectedCategoryId}
            onValueChange={setSelectedCategoryId}
          >
            <SelectTrigger aria-label="Select category" className="w-56">
              <SelectValue placeholder="Select category" />
            </SelectTrigger>
            <SelectContent>
              {categories.data.map((category) => (
                <SelectItem key={category.id} value={category.id}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </CardHeader>
      <CardContent className="min-w-0">
        {categoriesLoading || (selectedCategoryId && isLoading) ? (
          <Skeleton className="h-56 w-full" />
        ) : categoriesError || !categories ? (
          <QueryState message="Categories could not be loaded." />
        ) : categories.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Create a category to view its amount history.
          </p>
        ) : isError || !data ? (
          <QueryState message="Category history could not be loaded." />
        ) : (
          <div
            className="w-full min-w-0 max-w-full overflow-x-auto pb-2"
            data-testid="category-history-chart"
          >
            <div className="min-w-150">
              <div className="flex h-56 items-end gap-3 border-b border-l px-3 pt-4">
                {data.points.map((point, index) => {
                  const amount = amounts[index]
                  const value = amount ?? 0
                  const stateLabel =
                    point.state === "unknown"
                      ? "Amount unknown"
                      : point.state === "missing"
                        ? "No obligation"
                        : formatAmount(String(value), point.currency)
                  return (
                    <div
                      className="group flex h-full min-w-16 flex-1 flex-col"
                      key={periodValue(point.period)}
                      title={stateLabel}
                    >
                      <div className="relative flex min-h-0 flex-1 flex-col justify-end">
                        {point.state === "known" ? (
                          <span
                            className="min-h-1 rounded-t bg-chart-3/80 transition-colors group-hover:bg-chart-3"
                            style={{
                              height: `${Math.max((value / maximum) * 100, 1)}%`,
                            }}
                          />
                        ) : (
                          <span
                            className={
                              point.state === "unknown"
                                ? "min-h-1 rounded-t bg-amber-500/70"
                                : "min-h-1 rounded-t bg-muted"
                            }
                          />
                        )}
                      </div>
                      <div className="mt-2 h-9 text-center text-xs">
                        <span className="block text-muted-foreground">
                          {periodLabel(point.period)}
                        </span>
                        {point.state !== "known" && (
                          <span className="block text-amber-700 dark:text-amber-300">
                            {point.state === "unknown" ? "unknown" : "missing"}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                {currency ? `Amounts shown in ${currency}. ` : ""}Hover a bar
                for the exact amount.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function chartMaximum(values: number[]) {
  const maximum = Math.max(...values, 1)
  const desiredStep = maximum / 2
  const magnitude = 10 ** Math.floor(Math.log10(desiredStep))
  const normalized = desiredStep / magnitude
  const step =
    (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) *
    magnitude
  return step * 2
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
                        title={formatAmount(
                          String(amounts[index]),
                          currency === "No currency" ? null : currency,
                        )}
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
                        <div className="mt-2 h-9 text-center text-xs">
                          <span className="block text-muted-foreground">
                            {periodLabel(point.period)}
                          </span>
                          {!point.is_complete && (
                            <span className="block text-amber-700 dark:text-amber-300">
                              incomplete
                            </span>
                          )}
                        </div>
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
