import { useQuery } from "@tanstack/react-query"
import { Database } from "lucide-react"
import { useState } from "react"

import {
  ApiError,
  CategoriesService,
  type CategoryDataRecordPublic,
  type CategoryPublic,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) return "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (typeof value === "object") return "Unsupported value"
  return String(value)
}

function RecordCard({ record }: { record: CategoryDataRecordPublic }) {
  return (
    <section className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">
          Observed {formatTimestamp(record.observed_at)}
        </p>
        <div className="flex gap-2">
          <Badge variant="secondary">Schema v{record.schema_version}</Badge>
          {record.source && <Badge variant="outline">{record.source}</Badge>}
        </div>
      </div>
      <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        {Object.entries(record.data).map(([key, value]) => (
          <div key={key} className="flex justify-between gap-3">
            <dt className="text-muted-foreground">{key}</dt>
            <dd className="text-right font-medium">{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export function CategoryCustomDataDialog({
  ledgerId,
  category,
}: {
  ledgerId: string
  category: CategoryPublic
}) {
  const [open, setOpen] = useState(false)
  const recordsQuery = useQuery({
    queryKey: ["category-data-records", ledgerId, category.id],
    queryFn: async () => {
      try {
        return await CategoriesService.readCategoryDataRecords({
          ledgerId,
          categoryId: category.id,
        })
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
    enabled: open,
    retry: false,
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Database />
          <span className="sr-only">View custom data for {category.name}</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Custom data history for {category.name}</DialogTitle>
          <DialogDescription>
            Observations are ordered from newest to oldest and retain the schema
            version used when recorded.
          </DialogDescription>
        </DialogHeader>
        {recordsQuery.isLoading ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Loading custom data…
          </p>
        ) : recordsQuery.isError ? (
          <p className="rounded-md border border-destructive/50 p-3 text-sm text-destructive">
            Could not load the custom-data history.
          </p>
        ) : !recordsQuery.data || recordsQuery.data.count === 0 ? (
          <p className="rounded-md border border-dashed p-5 text-center text-sm text-muted-foreground">
            No custom data records have been saved for this category yet.
          </p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {recordsQuery.data.count} record
              {recordsQuery.data.count === 1 ? "" : "s"}
            </p>
            {recordsQuery.data.data.map((record) => (
              <RecordCard key={record.id} record={record} />
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
