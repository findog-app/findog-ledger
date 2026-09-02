import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, Link, notFound } from "@tanstack/react-router"
import { ArrowLeft, ListPlus } from "lucide-react"

import { CategoriesService } from "@/client"
import { CategoryCustomFieldsBuilder } from "@/components/Categories/CategoryCustomFieldsBuilder"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute(
  "/_layout/ledgers/$ledgerId/categories/$categoryId/custom-fields",
)({
  component: CategoryCustomFields,
  head: () => ({ meta: [{ title: "Custom fields - Findog Ledger" }] }),
})

function CategoryCustomFields() {
  const { ledgerId, categoryId } = Route.useParams()
  const { data: categories } = useSuspenseQuery({
    queryFn: () =>
      CategoriesService.readCategories({ ledgerId, includeArchived: true }),
    queryKey: ["categories", ledgerId, true],
  })
  const category = categories.data.find((item) => item.id === categoryId)

  if (!category) throw notFound()

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit" asChild>
        <Link to="/ledgers/$ledgerId/categories" params={{ ledgerId }}>
          <ArrowLeft />
          Back to categories
        </Link>
      </Button>
      <Card>
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <ListPlus className="size-5 text-primary" />
          </div>
          <CardTitle>Custom fields for {category.name}</CardTitle>
          <CardDescription>
            Define the data collected for this category. Saving creates a new
            schema version.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CategoryCustomFieldsBuilder
            ledgerId={ledgerId}
            category={category}
          />
        </CardContent>
      </Card>
    </div>
  )
}
