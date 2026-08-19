import { useSuspenseQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  Outlet,
  useLocation,
} from "@tanstack/react-router"
import { Settings, Tags } from "lucide-react"
import { Suspense } from "react"

import { LedgersService } from "@/client"
import { ObligationWorkspace } from "@/components/Obligations/ObligationWorkspace"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/_layout/ledgers/$ledgerId")({
  component: LedgerDetails,
  head: () => ({ meta: [{ title: "Ledger - Findog Ledger" }] }),
})

function LedgerDetails() {
  const { ledgerId } = Route.useParams()
  const location = useLocation()
  const { data: ledger } = useSuspenseQuery({
    queryFn: () => LedgersService.readLedger({ ledgerId }),
    queryKey: ["ledger", ledgerId],
  })

  if (location.pathname !== `/ledgers/${ledgerId}`) {
    return <Outlet />
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{ledger.name}</h1>
            <p className="mt-1 text-muted-foreground">
              {ledger.description ||
                "Review and manage obligations for this ledger."}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/ledgers/$ledgerId/categories" params={{ ledgerId }}>
                <Tags />
                Categories
              </Link>
            </Button>
            <Button variant="outline" size="icon" asChild>
              <Link
                to="/ledgers/$ledgerId/settings"
                params={{ ledgerId }}
                aria-label="Ledger settings"
              >
                <Settings />
              </Link>
            </Button>
          </div>
        </div>
      </div>
      <Suspense fallback={<ObligationWorkspaceSkeleton />}>
        <ObligationWorkspace ledgerId={ledgerId} />
      </Suspense>
    </div>
  )
}

function ObligationWorkspaceSkeleton() {
  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </CardContent>
    </Card>
  )
}
