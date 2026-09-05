import { createFileRoute } from "@tanstack/react-router"

import { AnalyticsDashboard } from "@/components/Analytics/AnalyticsDashboard"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useActiveLedger } from "@/hooks/useActiveLedger"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - Oblidog",
      },
    ],
  }),
})

function Dashboard() {
  const { activeLedger, isLoading } = useActiveLedger()

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />
  }

  if (activeLedger) {
    return <AnalyticsDashboard ledgerId={activeLedger.id} />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="max-w-xl truncate text-2xl font-semibold">Dashboard</h1>
        <p className="text-muted-foreground">
          Select a ledger to see its payment analytics.
        </p>
      </div>
      <section className="rounded-lg border bg-card p-6 text-card-foreground">
        <h2 className="text-lg font-medium">No ledger selected</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Create or select a ledger to get started.
        </p>
        <Button className="mt-4" asChild>
          <a href="/ledgers">Manage ledgers</a>
        </Button>
      </section>
    </div>
  )
}
