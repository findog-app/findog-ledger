import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ListPlus, Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useFieldArray, useForm } from "react-hook-form"
import { z } from "zod"

import {
  ApiError,
  CategoriesService,
  type CategoryDataSchemaCreate,
  type CategoryDataSchemaPublic,
  type CategoryPublic,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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

const fieldTypes = ["string", "number", "integer", "boolean", "date"] as const

const customFieldSchema = z.object({
  key: z
    .string()
    .trim()
    .regex(/^[A-Za-z_][A-Za-z0-9_]*$/, "Use letters, numbers, and underscores"),
  title: z.string().trim().optional(),
  description: z.string().trim().optional(),
  type: z.enum(fieldTypes),
  required: z.boolean(),
  minLength: z.number().int().nonnegative().optional(),
  maxLength: z.number().int().positive().optional(),
  minimum: z.number().optional(),
  maximum: z.number().optional(),
  enumValues: z.string().optional(),
})

const customFieldsSchema = z
  .object({ fields: z.array(customFieldSchema) })
  .superRefine(({ fields }, context) => {
    const keys = new Set<string>()
    fields.forEach((field, index) => {
      if (keys.has(field.key)) {
        context.addIssue({
          code: "custom",
          path: ["fields", index, "key"],
          message: "Field names must be unique",
        })
      }
      keys.add(field.key)
      if (
        field.minLength !== undefined &&
        field.maxLength !== undefined &&
        field.minLength > field.maxLength
      ) {
        context.addIssue({
          code: "custom",
          path: ["fields", index, "maxLength"],
          message: "Maximum length must be at least the minimum",
        })
      }
      if (
        field.minimum !== undefined &&
        field.maximum !== undefined &&
        field.minimum > field.maximum
      ) {
        context.addIssue({
          code: "custom",
          path: ["fields", index, "maximum"],
          message: "Maximum must be at least the minimum",
        })
      }
    })
  })

type CustomFieldsForm = z.infer<typeof customFieldsSchema>
type CustomField = CustomFieldsForm["fields"][number]
type JsonSchemaProperty = Record<string, unknown>

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
}

function unsupportedSchemaReason(schema: CategoryDataSchemaPublic | null) {
  if (!schema) return null
  if (!isRecord(schema.schema)) return "The schema root is not an object."

  const definition = schema.schema
  const supportedRootKeywords = new Set([
    "type",
    "properties",
    "required",
    "additionalProperties",
  ])
  const unsupportedRootKeyword = Object.keys(definition).find(
    (key) => !supportedRootKeywords.has(key),
  )
  if (unsupportedRootKeyword) {
    return `It uses the unsupported root keyword “${unsupportedRootKeyword}”.`
  }
  if (definition.type !== "object") {
    return "Its root type is not an object."
  }
  if (definition.additionalProperties !== false) {
    return "Its additional-properties setting is not supported by this builder."
  }
  const properties = definition.properties
  if (!isRecord(properties)) {
    return "Its properties definition is not an object."
  }
  if (
    !Array.isArray(definition.required) ||
    !definition.required.every((value) => typeof value === "string")
  ) {
    return "Its required-fields definition is not supported by this builder."
  }
  if (
    definition.required.some((key) => !Object.keys(properties).includes(key))
  ) {
    return "It requires a field that is not defined in its properties."
  }

  for (const [key, value] of Object.entries(properties)) {
    if (!isRecord(value)) return `Field “${key}” is not an object definition.`
    const type =
      value.type === "string" && value.format === "date" ? "date" : value.type
    if (!fieldTypes.includes(type as (typeof fieldTypes)[number])) {
      return `Field “${key}” uses an unsupported type or format.`
    }
    const supportedPropertyKeywords = new Set(["type", "title", "description"])
    if (type === "string") {
      supportedPropertyKeywords.add("minLength")
      supportedPropertyKeywords.add("maxLength")
      supportedPropertyKeywords.add("enum")
    }
    if (type === "date") supportedPropertyKeywords.add("format")
    if (type === "number" || type === "integer") {
      supportedPropertyKeywords.add("minimum")
      supportedPropertyKeywords.add("maximum")
    }
    const unsupportedPropertyKeyword = Object.keys(value).find(
      (propertyKey) => !supportedPropertyKeywords.has(propertyKey),
    )
    if (unsupportedPropertyKeyword) {
      return `Field “${key}” uses the unsupported keyword “${unsupportedPropertyKeyword}”.`
    }
    if (
      value.enum !== undefined &&
      (!Array.isArray(value.enum) ||
        !value.enum.every((item) => typeof item === "string"))
    ) {
      return `Field “${key}” has unsupported allowed values.`
    }
  }
  return null
}

function emptyField(): CustomField {
  return {
    key: "",
    title: "",
    description: "",
    type: "string",
    required: false,
    minLength: undefined,
    maxLength: undefined,
    minimum: undefined,
    maximum: undefined,
    enumValues: "",
  }
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined
}

function fieldsFromSchema(
  schema: CategoryDataSchemaPublic | null,
): CustomField[] {
  if (!schema?.schema || typeof schema.schema !== "object") return []
  const definition = schema.schema as Record<string, unknown>
  const properties = definition.properties
  const required = new Set(
    Array.isArray(definition.required)
      ? definition.required.filter(
          (value): value is string => typeof value === "string",
        )
      : [],
  )
  if (!properties || typeof properties !== "object") return []

  return Object.entries(properties).flatMap(([key, value]) => {
    if (!value || typeof value !== "object") return []
    const property = value as JsonSchemaProperty
    const type =
      property.type === "string" && property.format === "date"
        ? "date"
        : property.type
    if (!fieldTypes.includes(type as (typeof fieldTypes)[number])) return []
    return [
      {
        key,
        title: typeof property.title === "string" ? property.title : "",
        description:
          typeof property.description === "string" ? property.description : "",
        type: type as CustomField["type"],
        required: required.has(key),
        minLength: asNumber(property.minLength),
        maxLength: asNumber(property.maxLength),
        minimum: asNumber(property.minimum),
        maximum: asNumber(property.maximum),
        enumValues: Array.isArray(property.enum)
          ? property.enum
              .filter((item): item is string => typeof item === "string")
              .join(", ")
          : "",
      },
    ]
  })
}

function toSchema(fields: CustomFieldsForm["fields"]) {
  const properties = Object.fromEntries(
    fields.map((field) => {
      const property: JsonSchemaProperty = {
        type: field.type === "date" ? "string" : field.type,
      }
      if (field.type === "date") property.format = "date"
      if (field.title) property.title = field.title
      if (field.description) property.description = field.description
      if (field.type === "string") {
        if (field.minLength !== undefined) property.minLength = field.minLength
        if (field.maxLength !== undefined) property.maxLength = field.maxLength
        const values = field.enumValues
          ?.split(",")
          .map((value) => value.trim())
          .filter(Boolean)
        if (values?.length) property.enum = values
      }
      if (field.type === "number" || field.type === "integer") {
        if (field.minimum !== undefined) property.minimum = field.minimum
        if (field.maximum !== undefined) property.maximum = field.maximum
      }
      return [field.key, property]
    }),
  )
  return {
    type: "object",
    properties,
    required: fields
      .filter((field) => field.required)
      .map((field) => field.key),
    additionalProperties: false,
  }
}

function NumberInput({
  value,
  onChange,
  integer = false,
  placeholder,
}: {
  value: number | undefined
  onChange: (value: number | undefined) => void
  integer?: boolean
  placeholder: string
}) {
  return (
    <Input
      type="number"
      step={integer ? "1" : "any"}
      min={integer ? 0 : undefined}
      placeholder={placeholder}
      value={value ?? ""}
      onChange={(event) => {
        const nextValue = event.target.value
        onChange(nextValue === "" ? undefined : Number(nextValue))
      }}
    />
  )
}

export function CategoryCustomFieldsDialog({
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
  const form = useForm<CustomFieldsForm>({
    resolver: zodResolver(customFieldsSchema),
    defaultValues: { fields: [] },
  })
  const fields = useFieldArray({ control: form.control, name: "fields" })
  const unsupportedReason =
    schemaQuery.data === undefined
      ? null
      : unsupportedSchemaReason(schemaQuery.data)

  useEffect(() => {
    if (open && schemaQuery.data !== undefined) {
      form.reset({ fields: fieldsFromSchema(schemaQuery.data) })
    }
  }, [form, open, schemaQuery.data])

  const saveSchema = useMutation({
    mutationFn: (requestBody: CategoryDataSchemaCreate) =>
      CategoriesService.createCategoryDataSchema({
        ledgerId,
        categoryId: category.id,
        requestBody,
      }),
    onSuccess: (schema) => {
      showSuccessToast(
        `Custom fields saved as schema version ${schema.version}`,
      )
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: ["category-data-schema", ledgerId, category.id],
      }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <ListPlus />
          <span className="sr-only">
            Manage custom fields for {category.name}
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Custom fields for {category.name}</DialogTitle>
          <DialogDescription>
            Define the data collected for this category. Saving creates a new
            schema version.
          </DialogDescription>
        </DialogHeader>
        {schemaQuery.isLoading ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Loading fields…
          </p>
        ) : schemaQuery.isError ? (
          <p className="rounded-md border border-destructive/50 p-3 text-sm text-destructive">
            Could not load the current custom-field schema.
          </p>
        ) : (
          <form
            className="space-y-4"
            onSubmit={form.handleSubmit((data) => {
              if (!unsupportedReason) {
                saveSchema.mutate({ schema: toSchema(data.fields) })
              }
            })}
          >
            {unsupportedReason && (
              <p className="rounded-md border border-amber-500/50 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
                This schema is read-only in the custom-field builder.{" "}
                {unsupportedReason}
                Editing it here could remove configuration that the builder
                cannot represent.
              </p>
            )}
            <fieldset
              disabled={Boolean(unsupportedReason)}
              className="space-y-4"
            >
              {fields.fields.length === 0 ? (
                <p className="rounded-md border border-dashed p-5 text-center text-sm text-muted-foreground">
                  No custom fields configured yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {fields.fields.map((item, index) => {
                    const field = form.watch(`fields.${index}`)
                    const isText = field.type === "string"
                    const isNumeric =
                      field.type === "number" || field.type === "integer"
                    return (
                      <section
                        key={item.id}
                        className="space-y-3 rounded-lg border p-4"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <Badge variant="secondary">Field {index + 1}</Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => fields.remove(index)}
                          >
                            <Trash2 /> Remove
                          </Button>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="space-y-1.5 text-sm font-medium">
                            <Label htmlFor={`custom-field-key-${item.id}`}>
                              Field name
                            </Label>
                            <Input
                              id={`custom-field-key-${item.id}`}
                              {...form.register(`fields.${index}.key`)}
                              placeholder="meter_reading_kwh"
                            />
                            {form.formState.errors.fields?.[index]?.key && (
                              <span className="text-xs text-destructive">
                                {
                                  form.formState.errors.fields[index]?.key
                                    ?.message
                                }
                              </span>
                            )}
                          </div>
                          <div className="space-y-1.5 text-sm font-medium">
                            <Label htmlFor={`custom-field-type-${item.id}`}>
                              Type
                            </Label>
                            <Select
                              value={field.type}
                              onValueChange={(value) =>
                                form.setValue(
                                  `fields.${index}.type`,
                                  value as CustomField["type"],
                                )
                              }
                            >
                              <SelectTrigger
                                id={`custom-field-type-${item.id}`}
                                className="w-full"
                              >
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="string">Text</SelectItem>
                                <SelectItem value="number">Number</SelectItem>
                                <SelectItem value="integer">Integer</SelectItem>
                                <SelectItem value="boolean">
                                  Yes / no
                                </SelectItem>
                                <SelectItem value="date">Date</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="space-y-1.5 text-sm font-medium">
                            <Label htmlFor={`custom-field-title-${item.id}`}>
                              Label
                            </Label>
                            <Input
                              id={`custom-field-title-${item.id}`}
                              {...form.register(`fields.${index}.title`)}
                              placeholder="Meter reading"
                            />
                          </div>
                          <label className="flex items-center gap-2 pt-7 text-sm font-medium">
                            <input
                              type="checkbox"
                              {...form.register(`fields.${index}.required`)}
                            />{" "}
                            Required
                          </label>
                        </div>
                        <div className="space-y-1.5 text-sm font-medium">
                          <Label
                            htmlFor={`custom-field-description-${item.id}`}
                          >
                            Help text
                          </Label>
                          <Input
                            id={`custom-field-description-${item.id}`}
                            {...form.register(`fields.${index}.description`)}
                            placeholder="Shown below the field"
                          />
                        </div>
                        {isText && (
                          <div className="grid gap-3 sm:grid-cols-3">
                            <Label className="space-y-1.5">
                              Minimum length
                              <NumberInput
                                integer
                                value={field.minLength}
                                onChange={(value) =>
                                  form.setValue(
                                    `fields.${index}.minLength`,
                                    value,
                                  )
                                }
                                placeholder="None"
                              />
                            </Label>
                            <Label className="space-y-1.5">
                              Maximum length
                              <NumberInput
                                integer
                                value={field.maxLength}
                                onChange={(value) =>
                                  form.setValue(
                                    `fields.${index}.maxLength`,
                                    value,
                                  )
                                }
                                placeholder="None"
                              />
                            </Label>
                            <Label className="space-y-1.5">
                              Allowed values
                              <Input
                                {...form.register(`fields.${index}.enumValues`)}
                                placeholder="e.g. low, high"
                              />
                            </Label>
                          </div>
                        )}
                        {isNumeric && (
                          <div className="grid gap-3 sm:grid-cols-2">
                            <Label className="space-y-1.5">
                              Minimum
                              <NumberInput
                                value={field.minimum}
                                onChange={(value) =>
                                  form.setValue(
                                    `fields.${index}.minimum`,
                                    value,
                                  )
                                }
                                placeholder="None"
                              />
                            </Label>
                            <Label className="space-y-1.5">
                              Maximum
                              <NumberInput
                                value={field.maximum}
                                onChange={(value) =>
                                  form.setValue(
                                    `fields.${index}.maximum`,
                                    value,
                                  )
                                }
                                placeholder="None"
                              />
                            </Label>
                          </div>
                        )}
                      </section>
                    )
                  })}
                </div>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => fields.append(emptyField())}
              >
                <Plus /> Add field
              </Button>
              <DialogFooter>
                <LoadingButton type="submit" loading={saveSchema.isPending}>
                  Save custom fields
                </LoadingButton>
              </DialogFooter>
            </fieldset>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
