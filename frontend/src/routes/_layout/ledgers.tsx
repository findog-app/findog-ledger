import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/ledgers")({
  component: Ledgers,
  head: () => ({ meta: [{ title: "Ledgers - Findog Ledger" }] }),
})

function Ledgers() {
  return <Outlet />
}
