import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"

import AddLedger from "@/components/Ledgers/AddLedger"
import LedgerList from "@/components/Ledgers/LedgerList"
import PendingLedgers from "@/components/Ledgers/PendingLedgers"

export const Route = createFileRoute("/_layout/ledgers/")({
  component: LedgersIndex,
})

function LedgersIndex() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Ledgers</h1>
          <p className="text-muted-foreground">
            Keep separate workspaces for different areas of your finances.
          </p>
        </div>
        <AddLedger />
      </div>
      <Suspense fallback={<PendingLedgers />}>
        <LedgerList />
      </Suspense>
    </div>
  )
}
