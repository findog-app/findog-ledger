import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, Pencil, Plus, Trash2, Wrench } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type ObligationComponentCreate,
  type ObligationComponentPublic,
  ObligationsService,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { handleError } from "@/utils"

const componentTypes = [
  { value: "invoice", label: "Invoice" },
  { value: "invoice_item", label: "Invoice item" },
  { value: "adjustment", label: "Adjustment" },
  { value: "consumption", label: "Consumption" },
  { value: "other", label: "Other" },
]

type ComponentFormValues = {
  type: string
  customType: string
  label: string
  amount: string
}

type ComponentFormMode = "create" | ObligationComponentPublic | null

const emptyForm: ComponentFormValues = {
  type: "invoice",
  customType: "",
  label: "",
  amount: "",
}

function isIntegrationManaged(component: ObligationComponentPublic) {
  return component.source !== null || component.external_id !== null
}

function componentTypeLabel(type: string) {
  return componentTypes.find((option) => option.value === type)?.label ?? type
}

function amountLabel(amount: string | null, currency: string | null) {
  if (amount === null) return "—"
  return `${amount}${currency ? ` ${currency}` : ""}`
}

function FormFields({
  values,
  onChange,
  currency,
}: {
  values: ComponentFormValues
  onChange: (next: ComponentFormValues) => void
  currency: string | null
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-2">
        <Label htmlFor="component-type">Type</Label>
        <select
          id="component-type"
          className="border-input bg-background text-foreground h-9 w-full rounded-md border px-3 text-sm"
          value={values.type}
          onChange={(event) =>
            onChange({ ...values, type: event.target.value })
          }
        >
          {componentTypes.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {values.type === "other" ? (
        <div className="space-y-2">
          <Label htmlFor="component-custom-type">Custom type</Label>
          <Input
            id="component-custom-type"
            value={values.customType}
            maxLength={64}
            placeholder="e.g. meter reading"
            onChange={(event) =>
              onChange({ ...values, customType: event.target.value })
            }
          />
        </div>
      ) : null}
      <div className="space-y-2">
        <Label htmlFor="component-label">Label</Label>
        <Input
          id="component-label"
          value={values.label}
          maxLength={255}
          onChange={(event) =>
            onChange({ ...values, label: event.target.value })
          }
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="component-amount">Amount (optional)</Label>
        <div className="relative">
          <Input
            id="component-amount"
            className="pr-12 tabular-nums"
            type="number"
            step="0.01"
            inputMode="decimal"
            value={values.amount}
            onChange={(event) =>
              onChange({ ...values, amount: event.target.value })
            }
          />
          {currency ? (
            <span className="text-muted-foreground pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm">
              {currency}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function ComponentForm({
  component,
  currency,
  submitting,
  onCancel,
  onSubmit,
}: {
  component?: ObligationComponentPublic
  currency: string | null
  submitting: boolean
  onCancel: () => void
  onSubmit: (requestBody: ObligationComponentCreate) => void
}) {
  const [values, setValues] = useState<ComponentFormValues>(emptyForm)

  useEffect(() => {
    if (!component) {
      setValues(emptyForm)
      return
    }
    const knownType = componentTypes.some(
      ({ value }) => value === component.type,
    )
    setValues({
      type: knownType ? component.type : "other",
      customType: knownType ? "" : component.type,
      label: component.label,
      amount: component.amount ?? "",
    })
  }, [component])

  const type = values.type === "other" ? values.customType.trim() : values.type
  const canSubmit = type.length > 0 && values.label.trim().length > 0

  return (
    <form
      className="space-y-3 rounded-lg border bg-muted/30 p-4"
      onSubmit={(event) => {
        event.preventDefault()
        if (!canSubmit) return
        onSubmit({
          type,
          label: values.label.trim(),
          amount: values.amount === "" ? null : values.amount,
        })
      }}
    >
      <p className="font-medium">
        {component ? "Edit component" : "Add component"}
      </p>
      <FormFields values={values} onChange={setValues} currency={currency} />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <LoadingButton
          type="submit"
          size="sm"
          loading={submitting}
          disabled={!canSubmit}
        >
          {component ? "Save component" : "Add component"}
        </LoadingButton>
      </div>
    </form>
  )
}

export function ObligationComponentsSection({
  ledgerId,
  obligationKey,
  currency,
  canManage,
  onError,
  onSuccess,
}: {
  ledgerId: string
  obligationKey: string
  currency: string | null
  canManage: boolean
  onError: (message: string) => void
  onSuccess: (message: string) => void
}) {
  const queryClient = useQueryClient()
  const [formMode, setFormMode] = useState<ComponentFormMode>(null)
  const [removing, setRemoving] = useState<ObligationComponentPublic | null>(
    null,
  )
  const adding = formMode === "create"
  const editing = typeof formMode === "object" ? formMode : null
  const queryKey = ["obligation-components", ledgerId, obligationKey]
  const components = useQuery({
    queryKey,
    queryFn: () =>
      ObligationsService.readObligationComponents({ ledgerId, obligationKey }),
  })
  const invalidate = () => void queryClient.invalidateQueries({ queryKey })
  const create = useMutation({
    mutationFn: (requestBody: ObligationComponentCreate) =>
      ObligationsService.addObligationComponent({
        ledgerId,
        obligationKey,
        requestBody,
      }),
    onError: handleError.bind(onError),
    onSuccess: () => {
      onSuccess("Component added")
      setFormMode(null)
      invalidate()
    },
  })
  const update = useMutation({
    mutationFn: ({
      id,
      requestBody,
    }: {
      id: string
      requestBody: ObligationComponentCreate
    }) =>
      ObligationsService.updateObligationComponent({
        ledgerId,
        obligationKey,
        componentId: id,
        requestBody,
      }),
    onError: handleError.bind(onError),
    onSuccess: () => {
      onSuccess("Component updated")
      setFormMode(null)
      invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) =>
      ObligationsService.removeObligationComponent({
        ledgerId,
        obligationKey,
        componentId: id,
      }),
    onError: handleError.bind(onError),
    onSuccess: () => {
      onSuccess("Component removed")
      setRemoving(null)
      invalidate()
    },
  })

  return (
    <section
      className="space-y-3 border-t pt-4"
      aria-labelledby="components-heading"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 id="components-heading" className="font-semibold">
            Components
          </h3>
          <p className="text-muted-foreground text-xs">
            Informational details only; they are not summed into the obligation
            amount.
          </p>
        </div>
        {canManage && !adding && !editing ? (
          <Button size="sm" onClick={() => setFormMode("create")}>
            <Plus /> Add component
          </Button>
        ) : null}
      </div>

      {adding ? (
        <ComponentForm
          currency={currency}
          submitting={create.isPending}
          onCancel={() => setFormMode(null)}
          onSubmit={(requestBody) => create.mutate(requestBody)}
        />
      ) : null}
      {editing ? (
        <ComponentForm
          component={editing}
          currency={currency}
          submitting={update.isPending}
          onCancel={() => setFormMode(null)}
          onSubmit={(requestBody) =>
            update.mutate({ id: editing.id, requestBody })
          }
        />
      ) : null}

      {components.isLoading ? (
        <p className="text-muted-foreground text-sm">Loading components…</p>
      ) : null}
      {components.isError ? (
        <div className="flex items-center gap-3 text-sm text-destructive">
          <span>Unable to load components.</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void components.refetch()}
          >
            Try again
          </Button>
        </div>
      ) : null}
      {!components.isLoading &&
      !components.isError &&
      components.data?.data.length === 0 ? (
        <p className="text-muted-foreground text-sm">No components yet.</p>
      ) : null}
      {!components.isError && components.data?.data.length ? (
        <div className="space-y-2">
          {components.data.data.map((component) => {
            const managed = isIntegrationManaged(component)
            return (
              <article key={component.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">
                        {componentTypeLabel(component.type)}
                      </Badge>
                      {managed ? (
                        <Badge variant="outline" className="gap-1">
                          <Wrench className="size-3" /> Integration
                          {component.source ? ` · ${component.source}` : ""}
                        </Badge>
                      ) : (
                        <Badge variant="outline">Manual</Badge>
                      )}
                    </div>
                    <p className="break-words font-medium">{component.label}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold tabular-nums">
                      {amountLabel(component.amount, currency)}
                    </span>
                    {canManage && !managed ? (
                      <>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Edit ${component.label}`}
                          onClick={() => setFormMode(component)}
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Remove ${component.label}`}
                          onClick={() => setRemoving(component)}
                        >
                          <Trash2 />
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
                {managed ? (
                  <details className="mt-3 text-xs">
                    <summary className="text-muted-foreground flex cursor-pointer items-center gap-1">
                      <ChevronDown className="size-3" /> Technical details
                    </summary>
                    <dl className="mt-2 grid gap-1 break-all rounded bg-muted/50 p-2">
                      <div>
                        <dt className="inline text-muted-foreground">
                          Source:{" "}
                        </dt>
                        <dd className="inline">{component.source ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="inline text-muted-foreground">
                          External ID:{" "}
                        </dt>
                        <dd className="inline">
                          {component.external_id ?? "—"}
                        </dd>
                      </div>
                      {component.metadata ? (
                        <div>
                          <dt className="text-muted-foreground">Metadata</dt>
                          <dd>
                            <pre className="mt-1 whitespace-pre-wrap">
                              {JSON.stringify(component.metadata, null, 2)}
                            </pre>
                          </dd>
                        </div>
                      ) : null}
                    </dl>
                  </details>
                ) : null}
              </article>
            )
          })}
        </div>
      ) : null}

      {removing ? (
        <div className="border-destructive/40 bg-destructive/5 space-y-2 rounded-lg border p-3 text-sm">
          <p>
            Remove component <strong>{removing.label}</strong>? This cannot be
            undone.
          </p>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRemoving(null)}
            >
              Cancel
            </Button>
            <LoadingButton
              variant="destructive"
              size="sm"
              loading={remove.isPending}
              onClick={() => remove.mutate(removing.id)}
            >
              Remove component
            </LoadingButton>
          </div>
        </div>
      ) : null}
    </section>
  )
}
