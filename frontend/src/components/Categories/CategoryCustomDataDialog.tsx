import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Database, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"

import {
  ApiError,
  CategoriesService,
  type CategoryDataSchemaPublic,
  type CategoryPublic,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type FieldType = "string" | "number" | "integer" | "boolean" | "date"
type CustomDataForm = { data: Record<string, unknown> }

type SupportedField = {
  key: string
  label: string
  description: string | null
  type: FieldType
  enumValues: string[] | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function supportedFields(schema: CategoryDataSchemaPublic): {
  fields: SupportedField[]
  unsupportedReason: string | null
} {
  if (!isRecord(schema.schema)) {
    return {
      fields: [],
      unsupportedReason: "The schema root is not an object.",
    }
  }

  const definition = schema.schema
  if (definition.type !== "object" || !isRecord(definition.properties)) {
    return {
      fields: [],
      unsupportedReason: "The schema must define object properties.",
    }
  }
  if (definition.additionalProperties !== false) {
    return {
      fields: [],
      unsupportedReason:
        "Schemas that allow additional properties cannot be edited safely.",
    }
  }

  const fields: SupportedField[] = []
  for (const [key, value] of Object.entries(definition.properties)) {
    if (!isRecord(value)) {
      return {
        fields: [],
        unsupportedReason: `Field “${key}” is not an object definition.`,
      }
    }
    const type =
      value.type === "string" && value.format === "date" ? "date" : value.type
    if (
      !(["string", "number", "integer", "boolean", "date"] as const).includes(
        type as FieldType,
      )
    ) {
      return {
        fields: [],
        unsupportedReason: `Field “${key}” uses an unsupported type or format.`,
      }
    }
    if (
      value.enum !== undefined &&
      (!Array.isArray(value.enum) ||
        !value.enum.every((item) => typeof item === "string"))
    ) {
      return {
        fields: [],
        unsupportedReason: `Field “${key}” has unsupported allowed values.`,
      }
    }
    fields.push({
      key,
      label: typeof value.title === "string" ? value.title : key,
      description:
        typeof value.description === "string" ? value.description : null,
      type: type as FieldType,
      enumValues: Array.isArray(value.enum) ? (value.enum as string[]) : null,
    })
  }
  return { fields, unsupportedReason: null }
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

function fieldError(error: unknown): { key: string; message: string } | null {
  if (
    !(error instanceof ApiError) ||
    typeof error.body !== "object" ||
    !error.body
  ) {
    return null
  }
  const detail = (error.body as { detail?: unknown }).detail
  if (typeof detail !== "string") return null
  const separator = detail.indexOf(":")
  if (separator <= 0) return null
  return {
    key: detail.slice(0, separator),
    message: detail.slice(separator + 1).trim(),
  }
}

export function CategoryCustomDataDialog({
  ledgerId,
  category,
}: {
  ledgerId: string
  category: CategoryPublic
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const schemaQuery = useQuery({
    queryKey: ["category-data-schema", ledgerId, category.id],
    queryFn: async () => {
      try {
        return await CategoriesService.readCategoryDataSchema({
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
  const dataQuery = useQuery({
    queryKey: ["category-data", ledgerId, category.id],
    queryFn: async () => {
      try {
        return await CategoriesService.readCategoryData({
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
  const form = useForm<CustomDataForm>({ defaultValues: { data: {} } })
  const schema = schemaQuery.data
  const data = dataQuery.data
  const { fields, unsupportedReason } = schema
    ? supportedFields(schema)
    : { fields: [], unsupportedReason: null }

  useEffect(() => {
    if (open && dataQuery.data !== undefined) {
      form.reset({ data: dataQuery.data?.data ?? {} })
    }
  }, [dataQuery.data, form, open])

  const saveData = useMutation({
    mutationFn: (requestBody: CustomDataForm) =>
      CategoriesService.updateCategoryData({
        ledgerId,
        categoryId: category.id,
        requestBody,
      }),
    onSuccess: () => {
      showSuccessToast("Custom data saved")
      setOpen(false)
    },
    onError: (error) => {
      const parsedError = fieldError(error)
      if (
        parsedError &&
        fields.some((field) => field.key === parsedError.key)
      ) {
        form.setError(`data.${parsedError.key}`, {
          message: parsedError.message,
        })
        return
      }
      handleError.call(showErrorToast, error as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["category-data", ledgerId, category.id],
      })
    },
  })

  const loading = schemaQuery.isLoading || dataQuery.isLoading
  const queryError = schemaQuery.isError || dataQuery.isError

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Database />
          <span className="sr-only">Edit custom data for {category.name}</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Custom data for {category.name}</DialogTitle>
          <DialogDescription>
            Enter data using this category’s active custom-field schema.
          </DialogDescription>
        </DialogHeader>
        {loading ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Loading custom data…
          </p>
        ) : queryError ? (
          <p className="rounded-md border border-destructive/50 p-3 text-sm text-destructive">
            Could not load the custom data or schema.
          </p>
        ) : !schema ? (
          <p className="rounded-md border border-dashed p-5 text-center text-sm text-muted-foreground">
            No custom fields are configured for this category yet.
          </p>
        ) : unsupportedReason ? (
          <p className="rounded-md border border-amber-500/50 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
            This custom-data schema is read-only here. {unsupportedReason}
          </p>
        ) : (
          <form
            className="space-y-4"
            onSubmit={form.handleSubmit((values) => saveData.mutate(values))}
          >
            <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
              <p>Schema version {schema.version}</p>
              {data ? (
                <p className="mt-1">
                  Last updated {formatTimestamp(data.updated_at)}
                </p>
              ) : (
                <p className="mt-1">No saved custom data yet.</p>
              )}
            </div>
            {fields.map((field) => {
              const error = form.formState.errors.data?.[field.key]?.message
              const value = form.watch(`data.${field.key}`)
              return (
                <div key={field.key} className="space-y-1.5">
                  <Label htmlFor={`category-data-${category.id}-${field.key}`}>
                    {field.label}
                  </Label>
                  {field.enumValues ? (
                    <Select
                      value={typeof value === "string" ? value : ""}
                      onValueChange={(nextValue) =>
                        form.setValue(`data.${field.key}`, nextValue)
                      }
                    >
                      <SelectTrigger
                        id={`category-data-${category.id}-${field.key}`}
                        className="w-full"
                      >
                        <SelectValue placeholder="Choose a value" />
                      </SelectTrigger>
                      <SelectContent>
                        {field.enumValues.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : field.type === "boolean" ? (
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id={`category-data-${category.id}-${field.key}`}
                        checked={value === true}
                        onCheckedChange={(checked) =>
                          form.setValue(`data.${field.key}`, checked === true)
                        }
                      />
                      <Label
                        htmlFor={`category-data-${category.id}-${field.key}`}
                        className="font-normal"
                      >
                        Yes
                      </Label>
                    </div>
                  ) : (
                    <Input
                      id={`category-data-${category.id}-${field.key}`}
                      type={
                        field.type === "date"
                          ? "date"
                          : field.type === "string"
                            ? "text"
                            : "number"
                      }
                      step={field.type === "integer" ? "1" : undefined}
                      value={
                        typeof value === "string" || typeof value === "number"
                          ? value
                          : ""
                      }
                      onChange={(event) => {
                        const nextValue = event.target.value
                        form.setValue(
                          `data.${field.key}`,
                          field.type === "number" || field.type === "integer"
                            ? nextValue === ""
                              ? undefined
                              : Number(nextValue)
                            : nextValue,
                        )
                      }}
                    />
                  )}
                  {field.description && (
                    <p className="text-sm text-muted-foreground">
                      {field.description}
                    </p>
                  )}
                  {error && (
                    <p className="text-sm text-destructive">{String(error)}</p>
                  )}
                </div>
              )
            })}
            <DialogFooter>
              <LoadingButton type="submit" loading={saveData.isPending}>
                <Save /> Save custom data
              </LoadingButton>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
