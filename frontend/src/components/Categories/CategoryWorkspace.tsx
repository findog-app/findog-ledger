import { zodResolver } from "@hookform/resolvers/zod"
import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { Archive, FolderPlus, Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  CategoriesService,
  type CategoryCreate,
  type CategoryGroupCreate,
} from "@/client"
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

const categorySchema = z.object({
  category_group_id: z.string().min(1, "Choose a group"),
  name: z.string().trim().min(1, "Name is required").max(255),
  description: z.string().optional(),
})

type GroupFormData = z.infer<typeof groupSchema>
type CategoryFormData = z.infer<typeof categorySchema>

function useCategoryQueries(ledgerId: string) {
  const groups = useSuspenseQuery({
    queryFn: () =>
      CategoriesService.readCategoryGroups({
        ledgerId,
        includeArchived: true,
      }),
    queryKey: ["category-groups", ledgerId],
  })
  const categories = useSuspenseQuery({
    queryFn: () =>
      CategoriesService.readCategories({
        ledgerId,
        includeArchived: true,
      }),
    queryKey: ["categories", ledgerId],
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
    defaultValues: { category_group_id: "", name: "", description: "" },
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
      <DialogContent>
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
              }),
            )}
            className="space-y-4"
          >
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
  const { categories, groups } = useCategoryQueries(ledgerId)
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
                    </div>
                    <div className="flex items-center gap-2">
                      {!category.is_active && (
                        <Badge variant="secondary">Archived</Badge>
                      )}
                      {category.is_active && (
                        <ArchiveButton
                          label={category.name}
                          onArchive={() => archiveCategory.mutate(category.id)}
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
  )
}

export default CategoryWorkspace
