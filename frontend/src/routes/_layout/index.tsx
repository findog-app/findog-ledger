import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - Findog Ledger",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="max-w-xl truncate text-2xl font-semibold">
          {currentUser?.full_name || currentUser?.email}
        </h1>
        <p className="text-muted-foreground">
          Private payment-obligation repository foundation.
        </p>
      </div>
      <section className="rounded-lg border bg-card p-6 text-card-foreground">
        <h2 className="text-lg font-medium">Current Scope</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Authentication, admin-managed users, ledgers, and category management
          are available. Counterparties, categories, obligations, and
          integration sync are next in the business workflow.
        </p>
      </section>
      {currentUser?.is_superuser ? (
        <section className="rounded-lg border border-dashed p-6">
          <h2 className="text-lg font-medium">Admin Access</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use the admin section to provision users and manage account status.
          </p>
        </section>
      ) : null}
    </div>
  )
}
