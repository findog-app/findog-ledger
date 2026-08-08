import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Archive, ArrowLeft, BookOpen } from "lucide-react"
import { useEffect, useState } from "react"

import { LedgersService } from "@/client"
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
import { Label } from "@/components/ui/label"

export const Route = createFileRoute("/_layout/ledgers/$ledgerId/settings")({
  component: LedgerSettings,
  head: () => ({ meta: [{ title: "Ledger Settings - Findog Ledger" }] }),
})

function LedgerSettings() {
  const { ledgerId } = Route.useParams()
  const { data: ledger } = useSuspenseQuery({
    queryFn: () => LedgersService.readLedger({ ledgerId }),
    queryKey: ["ledger", ledgerId],
  })
  const [includeArchived, setIncludeArchived] = useState(() => {
    if (typeof window === "undefined") return false
    return (
      window.localStorage.getItem(`show-archived-categories:${ledgerId}`) ===
      "true"
    )
  })

  useEffect(() => {
    window.localStorage.setItem(
      `show-archived-categories:${ledgerId}`,
      String(includeArchived),
    )
  }, [includeArchived, ledgerId])

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
            <BookOpen className="size-5 text-primary" />
            <Badge variant="outline">Ledger settings</Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{ledger.name}</h1>
          <p className="mt-1 text-muted-foreground">
            Configure how this ledger workspace behaves.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Archive className="size-5" />
            Category visibility
          </CardTitle>
          <CardDescription>
            Choose whether archived groups and categories should be shown in the
            workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Checkbox
              id="show-archived-categories"
              checked={includeArchived}
              onCheckedChange={(checked) =>
                setIncludeArchived(checked === true)
              }
            />
            <Label htmlFor="show-archived-categories">Show archived</Label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
