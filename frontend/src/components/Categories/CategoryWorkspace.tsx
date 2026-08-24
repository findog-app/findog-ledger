import { zodResolver } from "@hookform/resolvers/zod"
import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { Archive, FolderPlus, Pencil, Plus } from "lucide-react"
import { useEffect, useState } from "react"
import {
  type Control,
  type FieldValues,
  type Path,
  useForm,
  useWatch,
} from "react-hook-form"
import { z } from "zod"

import {
  CategoriesService,
  type CategoryCreate,
  type CategoryGroupCreate,
  type CategoryGroupUpdate,
  type CategoryPublic,
  type CategoryUpdate,
} from "@/client"
import { CategoryCustomFieldsDialog } from "@/components/Categories/CategoryCustomFieldsDialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
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

const groupSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255),
  description: z.string().optional(),
})

const categoryConfigurationSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255),
  description: z.string().optional(),
  data_source_policy: z.enum(["manual", "automatic", "hybrid"]),
  recurrence_interval: z.number().int().positive().optional(),
  recurrence_unit: z.enum(["month", "year"]).optional(),
  first_due_date: z.string().optional(),
  currency: z.enum(["PLN", "EUR", "USD", "GBP", "CHF"]),
})

const categorySchema = categoryConfigurationSchema.extend({
  category_group_id: z.string().min(1, "Choose a group"),
  code: z
    .string()
    .trim()
    .regex(/^[A-Z]{4}$/, "Code must contain exactly 4 uppercase letters"),
})

type GroupFormData = z.infer<typeof groupSchema>
type CategoryFormData = z.infer<typeof categorySchema>
type CategoryUpdateFormData = z.infer<typeof categoryConfigurationSchema>

function CurrencyField<T extends FieldValues>({
  control,
}: {
  control: Control<T>
}) {
  return (
    <FormField
      control={control}
      name={"currency" as Path<T>}
      render={({ field }) => (
        <FormItem>
          <FormLabel>Currency</FormLabel>
          <Select onValueChange={field.onChange} value={field.value as string}>
            <FormControl>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              <SelectItem value="PLN">PLN</SelectItem>
              <SelectItem value="EUR">EUR</SelectItem>
              <SelectItem value="USD">USD</SelectItem>
              <SelectItem value="GBP">GBP</SelectItem>
              <SelectItem value="CHF">CHF</SelectItem>
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}

function obligationModeDescription(mode: "manual" | "automatic" | "hybrid") {
  if (mode === "manual") {
    return "Obligations for this category are created manually."
  }
  if (mode === "automatic") {
    return "Obligations are created automatically from the payment schedule."
  }
  return "Obligations follow the schedule and can also be created manually."
}

function nextPaymentDate(
  firstDueDate: string | undefined,
  interval: number | undefined,
  unit: "month" | "year" | undefined,
): Date | undefined {
  if (!firstDueDate || !interval || !unit) return undefined

  const [year, month, day] = firstDueDate.split("-").map(Number)
  if (!year || !month || !day) return undefined

  const addMonths = (value: Date, months: number) => {
    const targetMonth = value.getMonth() + months
    const targetYear = value.getFullYear() + Math.floor(targetMonth / 12)
    const normalizedMonth = ((targetMonth % 12) + 12) % 12
    const lastDay = new Date(targetYear, normalizedMonth + 1, 0).getDate()
    return new Date(targetYear, normalizedMonth, Math.min(day, lastDay))
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  let occurrence = new Date(year, month - 1, day)
  const monthsToAdd = unit === "year" ? interval * 12 : interval

  while (occurrence <= today) {
    occurrence = addMonths(occurrence, monthsToAdd)
  }

  return occurrence
}

function recurrencePreset(
  interval: number | undefined,
  unit: "month" | "year" | undefined,
) {
  if (interval === 1 && unit === "month") return "monthly"
  if (interval === 2 && unit === "month") return "every-two-months"
  if (interval === 1 && unit === "year") return "yearly"
  return "custom"
}

function PaymentScheduleFields<T extends FieldValues>({
  control,
  onPresetChange,
}: {
  control: Control<T>
  onPresetChange: (preset: string) => void
}) {
  const interval = useWatch({
    control,
    name: "recurrence_interval" as Path<T>,
  }) as number | undefined
  const unit = useWatch({
    control,
    name: "recurrence_unit" as Path<T>,
  }) as "month" | "year" | undefined
  const firstDueDate = useWatch({
    control,
    name: "first_due_date" as Path<T>,
  }) as string | undefined
  const preset = recurrencePreset(interval, unit)
  const nextDueDate = nextPaymentDate(
    firstDueDate,
    interval ?? 1,
    unit ?? "month",
  )

  return (
    <section className="space-y-4 border-t pt-4">
      <div>
        <h3 className="text-sm font-semibold">Payment schedule</h3>
        <p className="text-sm text-muted-foreground">
          Set when the first payment is due and how often it repeats.
        </p>
      </div>
      <FormField
        control={control}
        name={"first_due_date" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>First payment due</FormLabel>
            <FormControl>
              <Input
                type="date"
                {...field}
                value={(field.value as string) ?? ""}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormItem>
        <FormLabel>Repeat</FormLabel>
        <Select
          onValueChange={(value) => {
            onPresetChange(value)
          }}
          value={preset}
        >
          <FormControl>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
          </FormControl>
          <SelectContent>
            <SelectItem value="monthly">Every month</SelectItem>
            <SelectItem value="every-two-months">Every 2 months</SelectItem>
            <SelectItem value="yearly">Every year</SelectItem>
            <SelectItem value="custom">Custom</SelectItem>
          </SelectContent>
        </Select>
      </FormItem>
      {preset === "custom" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={control}
            name={"recurrence_interval" as Path<T>}
            render={({ field }) => (
              <FormItem>
                <FormLabel>Every</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    value={(field.value as number | undefined) ?? ""}
                    onChange={(event) =>
                      field.onChange(
                        event.target.value === ""
                          ? undefined
                          : Number(event.target.value),
                      )
                    }
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={control}
            name={"recurrence_unit" as Path<T>}
            render={({ field }) => (
              <FormItem>
                <FormLabel>Period</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  value={field.value as string}
                >
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Choose a period" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="month">Months</SelectItem>
                    <SelectItem value="year">Years</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      )}
      <div className="rounded-md bg-muted p-3">
        <p className="text-sm font-medium">Next payment</p>
        {nextDueDate ? (
          <p className="mt-1 text-sm text-muted-foreground">
            {new Intl.DateTimeFormat("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            }).format(nextDueDate)}
          </p>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">
            Choose the first payment due date to see the next occurrence.
          </p>
        )}
      </div>
    </section>
  )
}

function useCategoryQueries(ledgerId: string, includeArchived: boolean) {
  const groups = useSuspenseQuery({
    queryFn: () =>
      CategoriesService.readCategoryGroups({
        ledgerId,
        includeArchived,
      }),
    queryKey: ["category-groups", ledgerId, includeArchived],
  })
  const categories = useSuspenseQuery({
    queryFn: () =>
      CategoriesService.readCategories({
        ledgerId,
        includeArchived,
      }),
    queryKey: ["categories", ledgerId, includeArchived],
  })

  return { categories: categories.data.data, groups: groups.data.data }
}

function CreateGroupDialog({ ledgerId }: { ledgerId: string }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<GroupFormData>({
    resolver: zodResolver(groupSchema),
    defaultValues: { name: "", description: "" },
  })
  const mutation = useMutation({
    mutationFn: (data: CategoryGroupCreate) =>
      CategoriesService.createCategoryGroup({ ledgerId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Category group created")
      form.reset()
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: ["category-groups", ledgerId],
      }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <FolderPlus />
          New group
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create category group</DialogTitle>
          <DialogDescription>
            Groups keep related categories together.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              mutation.mutate({
                ...data,
                description: data.description || null,
              }),
            )}
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Utilities" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Optional description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Create group
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function EditGroupDialog({
  ledgerId,
  group,
}: {
  ledgerId: string
  group: { id: string; name: string; description: string | null }
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<GroupFormData>({
    resolver: zodResolver(groupSchema),
    defaultValues: { name: group.name, description: group.description ?? "" },
  })

  useEffect(() => {
    if (open) {
      form.reset({ name: group.name, description: group.description ?? "" })
    }
  }, [form, group.description, group.name, open])

  const mutation = useMutation({
    mutationFn: (data: CategoryGroupUpdate) =>
      CategoriesService.updateCategoryGroup({
        ledgerId,
        categoryGroupId: group.id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Category group updated")
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({
        queryKey: ["category-groups", ledgerId],
      }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Pencil />
          <span className="sr-only">Edit {group.name}</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit category group</DialogTitle>
          <DialogDescription>
            Update the name or description of this group.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              mutation.mutate({
                ...data,
                description: data.description || null,
              }),
            )}
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Optional description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save group changes
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function CreateCategoryDialog({
  ledgerId,
  groups,
}: {
  ledgerId: string
  groups: { id: string; name: string; is_active: boolean }[]
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const activeGroups = groups.filter((group) => group.is_active)
  const form = useForm<CategoryFormData>({
    resolver: zodResolver(categorySchema),
    defaultValues: {
      category_group_id: "",
      name: "",
      description: "",
      code: "",
      data_source_policy: "hybrid",
      recurrence_interval: 1,
      recurrence_unit: "month",
      first_due_date: "",
      currency: "PLN",
    },
  })
  const mutation = useMutation({
    mutationFn: (data: CategoryCreate) =>
      CategoriesService.createCategory({ ledgerId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Category created")
      form.reset()
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["categories", ledgerId] }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={activeGroups.length === 0}>
          <Plus />
          New category
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create category</DialogTitle>
          <DialogDescription>
            Add a category to an active group.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              mutation.mutate({
                ...data,
                description: data.description || null,
                first_due_date: data.first_due_date || null,
              }),
            )}
            className="space-y-4"
          >
            <h3 className="text-sm font-semibold">Basic information</h3>
            <FormField
              control={form.control}
              name="category_group_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Group</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Choose a group" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {activeGroups.map((group) => (
                        <SelectItem key={group.id} value={group.id}>
                          {group.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Electricity" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Optional description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Code</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="ELEC"
                      maxLength={4}
                      {...field}
                      onChange={(event) =>
                        field.onChange(event.target.value.toUpperCase())
                      }
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <section className="space-y-4 border-t pt-4">
              <div>
                <h3 className="text-sm font-semibold">Behavior</h3>
                <p className="text-sm text-muted-foreground">
                  Choose how obligations are created and managed.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="data_source_policy"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category mode</FormLabel>
                      <Select
                        onValueChange={(value) => {
                          field.onChange(value)
                          if (
                            value !== "manual" &&
                            (!form.getValues("recurrence_interval") ||
                              !form.getValues("recurrence_unit"))
                          ) {
                            form.setValue("recurrence_interval", 1)
                            form.setValue("recurrence_unit", "month")
                          }
                        }}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="manual">Manual</SelectItem>
                          <SelectItem value="automatic">Automatic</SelectItem>
                          <SelectItem value="hybrid">Hybrid</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <CurrencyField control={form.control} />
              </div>
              <p className="text-sm text-muted-foreground">
                {obligationModeDescription(form.watch("data_source_policy"))}
              </p>
            </section>
            {form.watch("data_source_policy") !== "manual" && (
              <PaymentScheduleFields
                control={form.control}
                onPresetChange={(preset) => {
                  if (preset === "monthly") {
                    form.setValue("recurrence_interval", 1)
                    form.setValue("recurrence_unit", "month")
                  } else if (preset === "every-two-months") {
                    form.setValue("recurrence_interval", 2)
                    form.setValue("recurrence_unit", "month")
                  } else if (preset === "yearly") {
                    form.setValue("recurrence_interval", 1)
                    form.setValue("recurrence_unit", "year")
                  } else if (preset === "custom") {
                    form.setValue("recurrence_interval", 3)
                    form.setValue("recurrence_unit", "month")
                  }
                }}
              />
            )}
            <DialogFooter>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Create category
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function EditCategoryDialog({
  ledgerId,
  category,
}: {
  ledgerId: string
  category: CategoryPublic
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const form = useForm<CategoryUpdateFormData>({
    resolver: zodResolver(categoryConfigurationSchema),
    defaultValues: {
      name: category.name,
      description: category.description ?? "",
      data_source_policy: category.data_source_policy,
      recurrence_interval: category.recurrence_interval ?? undefined,
      recurrence_unit: category.recurrence_unit ?? undefined,
      first_due_date: category.first_due_date ?? "",
      currency: category.currency,
    },
  })

  useEffect(() => {
    if (open) {
      form.reset({
        name: category.name,
        description: category.description ?? "",
        data_source_policy: category.data_source_policy,
        recurrence_interval: category.recurrence_interval ?? undefined,
        recurrence_unit: category.recurrence_unit ?? undefined,
        first_due_date: category.first_due_date ?? "",
        currency: category.currency,
      })
    }
  }, [category, form, open])

  const mutation = useMutation({
    mutationFn: (data: CategoryUpdate) =>
      CategoriesService.updateCategory({
        ledgerId,
        categoryId: category.id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Category updated")
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["categories", ledgerId] }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Pencil />
          <span className="sr-only">Edit {category.name}</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit category</DialogTitle>
          <DialogDescription>
            Update the category and its obligation configuration.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              mutation.mutate({
                name: data.name,
                description: data.description || null,
                data_source_policy: data.data_source_policy,
                recurrence_interval: data.recurrence_interval,
                recurrence_unit: data.recurrence_unit ?? null,
                first_due_date: data.first_due_date || null,
                currency: data.currency,
              }),
            )}
            className="space-y-4"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Optional description" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="space-y-2">
              <p className="text-sm font-medium">Code</p>
              <Badge variant="secondary">{category.code}</Badge>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="data_source_policy"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category mode</FormLabel>
                    <Select
                      onValueChange={(value) => {
                        field.onChange(value)
                        if (
                          value !== "manual" &&
                          (!form.getValues("recurrence_interval") ||
                            !form.getValues("recurrence_unit"))
                        ) {
                          form.setValue("recurrence_interval", 1)
                          form.setValue("recurrence_unit", "month")
                        }
                      }}
                      value={field.value}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="manual">Manual</SelectItem>
                        <SelectItem value="automatic">Automatic</SelectItem>
                        <SelectItem value="hybrid">Hybrid</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <CurrencyField control={form.control} />
            </div>
            <p className="text-sm text-muted-foreground">
              {obligationModeDescription(form.watch("data_source_policy"))}
            </p>
            {form.watch("data_source_policy") !== "manual" && (
              <PaymentScheduleFields
                control={form.control}
                onPresetChange={(preset) => {
                  if (preset === "monthly") {
                    form.setValue("recurrence_interval", 1)
                    form.setValue("recurrence_unit", "month")
                  } else if (preset === "every-two-months") {
                    form.setValue("recurrence_interval", 2)
                    form.setValue("recurrence_unit", "month")
                  } else if (preset === "yearly") {
                    form.setValue("recurrence_interval", 1)
                    form.setValue("recurrence_unit", "year")
                  } else if (preset === "custom") {
                    form.setValue("recurrence_interval", 3)
                    form.setValue("recurrence_unit", "month")
                  }
                }}
              />
            )}
            <DialogFooter>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save changes
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function ArchiveButton({
  label,
  onArchive,
}: {
  label: string
  onArchive: () => void
}) {
  return (
    <Button variant="ghost" size="sm" onClick={onArchive}>
      <Archive />
      <span className="sr-only">Archive {label}</span>
    </Button>
  )
}

export function CategoryWorkspace({ ledgerId }: { ledgerId: string }) {
  const [includeArchived] = useState(() => {
    if (typeof window === "undefined") return false
    return (
      window.localStorage.getItem(`show-archived-categories:${ledgerId}`) ===
      "true"
    )
  })
  const { categories, groups } = useCategoryQueries(ledgerId, includeArchived)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const archiveGroup = useMutation({
    mutationFn: (groupId: string) =>
      CategoriesService.archiveCategoryGroup({
        ledgerId,
        categoryGroupId: groupId,
      }),
    onSuccess: () => showSuccessToast("Category group archived"),
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["category-groups", ledgerId] })
      queryClient.invalidateQueries({ queryKey: ["categories", ledgerId] })
    },
  })
  const archiveCategory = useMutation({
    mutationFn: (categoryId: string) =>
      CategoriesService.archiveCategory({ ledgerId, categoryId }),
    onSuccess: () => showSuccessToast("Category archived"),
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["categories", ledgerId] }),
  })

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Category groups</CardTitle>
              <CardDescription>Organize categories by purpose.</CardDescription>
            </div>
            <CreateGroupDialog ledgerId={ledgerId} />
          </CardHeader>
          <CardContent>
            {groups.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No groups yet.
              </p>
            ) : (
              <div className="divide-y rounded-lg border">
                {groups.map((group) => (
                  <div
                    key={group.id}
                    className="flex items-center justify-between gap-3 p-4"
                  >
                    <div className="min-w-0">
                      <p
                        className={
                          group.is_active
                            ? "font-medium"
                            : "font-medium text-muted-foreground line-through"
                        }
                      >
                        {group.name}
                      </p>
                      {group.description && (
                        <p className="truncate text-sm text-muted-foreground">
                          {group.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <EditGroupDialog ledgerId={ledgerId} group={group} />
                      {!group.is_active && (
                        <Badge variant="secondary">Archived</Badge>
                      )}
                      {group.is_active && (
                        <ArchiveButton
                          label={group.name}
                          onArchive={() => archiveGroup.mutate(group.id)}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Categories</CardTitle>
              <CardDescription>
                Use categories to classify obligations.
              </CardDescription>
            </div>
            <CreateCategoryDialog ledgerId={ledgerId} groups={groups} />
          </CardHeader>
          <CardContent>
            {categories.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No categories yet.
              </p>
            ) : (
              <div className="divide-y rounded-lg border">
                {categories.map((category) => {
                  const group = groups.find(
                    (item) => item.id === category.category_group_id,
                  )
                  return (
                    <div
                      key={category.id}
                      className="flex items-center justify-between gap-3 p-4"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p
                            className={
                              category.is_active
                                ? "font-medium"
                                : "font-medium text-muted-foreground line-through"
                            }
                          >
                            {category.name}
                          </p>
                          <Badge variant="outline">
                            {group?.name || "Unknown group"}
                          </Badge>
                        </div>
                        {category.description && (
                          <p className="truncate text-sm text-muted-foreground">
                            {category.description}
                          </p>
                        )}
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {category.code && (
                            <Badge variant="secondary">{category.code}</Badge>
                          )}
                          <Badge variant="outline">
                            {category.data_source_policy}
                          </Badge>
                          <Badge variant="outline">
                            {category.recurrence_interval &&
                            category.recurrence_unit
                              ? `every ${category.recurrence_interval} ${category.recurrence_unit}${category.recurrence_interval === 1 ? "" : "s"}`
                              : "no recurrence"}
                          </Badge>
                          {category.currency && (
                            <Badge variant="outline">{category.currency}</Badge>
                          )}
                          {category.first_due_date && (
                            <Badge variant="outline">
                              first due {category.first_due_date}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <CategoryCustomFieldsDialog
                          ledgerId={ledgerId}
                          category={category}
                        />
                        <EditCategoryDialog
                          ledgerId={ledgerId}
                          category={category}
                        />
                        {!category.is_active && (
                          <Badge variant="secondary">Archived</Badge>
                        )}
                        {category.is_active && (
                          <ArchiveButton
                            label={category.name}
                            onArchive={() =>
                              archiveCategory.mutate(category.id)
                            }
                          />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default CategoryWorkspace
