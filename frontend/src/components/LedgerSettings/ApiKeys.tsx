import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { Check, Copy, KeyRound, Plus, Trash2 } from "lucide-react"
import { useState } from "react"

import { type ApiKeyCreated, LedgersService } from "@/client"
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
import {
  Dialog,
  DialogClose,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const apiKeyScopes = ["ledger:read", "ledger:write"] as const

function formatDate(value: string | null) {
  if (!value) return "Never"
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

export function ApiKeys({ ledgerId }: { ledgerId: string }) {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const { data: apiKeys } = useSuspenseQuery({
    queryFn: () => LedgersService.readApiKeys({ ledgerId }),
    queryKey: ["api-keys", ledgerId],
  })
  const [createOpen, setCreateOpen] = useState(false)
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null)
  const [name, setName] = useState("")
  const [expiresAt, setExpiresAt] = useState("")
  const [scopes, setScopes] = useState<Set<(typeof apiKeyScopes)[number]>>(
    () => new Set(["ledger:read"]),
  )
  const createMutation = useMutation({
    mutationFn: () =>
      LedgersService.createApiKey({
        ledgerId,
        requestBody: {
          name: name.trim(),
          scopes: [...scopes],
          expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        },
      }),
    onSuccess: (apiKey) => {
      setCreatedKey(apiKey)
      setCreateOpen(false)
      setName("")
      setExpiresAt("")
      setScopes(new Set(["ledger:read"]))
      void queryClient.invalidateQueries({ queryKey: ["api-keys", ledgerId] })
    },
    onError: handleError.bind(showErrorToast),
  })
  const revokeMutation = useMutation({
    mutationFn: (apiKeyId: string) =>
      LedgersService.revokeApiKey({ apiKeyId, ledgerId }),
    onSuccess: () => {
      showSuccessToast("API key revoked")
      void queryClient.invalidateQueries({ queryKey: ["api-keys", ledgerId] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const toggleScope = (
    scope: (typeof apiKeyScopes)[number],
    checked: boolean,
  ) => {
    setScopes((current) => {
      const next = new Set(current)
      if (checked) next.add(scope)
      else next.delete(scope)
      return next
    })
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-5" />
            API keys
          </CardTitle>
          <CardDescription>
            Create ledger-scoped credentials for integrations. A key is shown
            only once when it is created.
          </CardDescription>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button className="shrink-0">
              <Plus /> New key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create API key</DialogTitle>
              <DialogDescription>
                Choose a descriptive name and only the scopes the integration
                needs.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="api-key-name">Name</Label>
                <Input
                  id="api-key-name"
                  placeholder="Invoice importer"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={255}
                />
              </div>
              <div className="space-y-2">
                <Label>Scopes</Label>
                {apiKeyScopes.map((scope) => (
                  <div key={scope} className="flex items-center gap-2">
                    <Checkbox
                      id={`api-key-scope-${scope}`}
                      checked={scopes.has(scope)}
                      onCheckedChange={(checked) =>
                        toggleScope(scope, checked === true)
                      }
                    />
                    <Label htmlFor={`api-key-scope-${scope}`}>{scope}</Label>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <Label htmlFor="api-key-expires-at">
                  Expires at (optional)
                </Label>
                <Input
                  id="api-key-expires-at"
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(event) => setExpiresAt(event.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={createMutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton
                loading={createMutation.isPending}
                disabled={!name.trim() || scopes.size === 0}
                onClick={() => createMutation.mutate()}
              >
                Create key
              </LoadingButton>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        {apiKeys.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">No API keys yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Last used</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead aria-label="Actions" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.data.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell>
                    <div className="font-medium">{apiKey.name}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {apiKey.key_prefix}…
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {apiKey.scopes.map((scope) => (
                        <Badge key={scope} variant="outline">
                          {scope}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{formatDate(apiKey.last_used_at)}</TableCell>
                  <TableCell>{formatDate(apiKey.expires_at)}</TableCell>
                  <TableCell>
                    {apiKey.revoked_at ? (
                      <Badge variant="secondary">Revoked</Badge>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Revoke ${apiKey.name}`}
                        disabled={revokeMutation.isPending}
                        onClick={() => revokeMutation.mutate(apiKey.id)}
                      >
                        <Trash2 className="text-destructive" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
      <CreatedKeyDialog
        apiKey={createdKey}
        onClose={() => setCreatedKey(null)}
      />
    </Card>
  )
}

function CreatedKeyDialog({
  apiKey,
  onClose,
}: {
  apiKey: ApiKeyCreated | null
  onClose: () => void
}) {
  const [copiedText, copy] = useCopyToClipboard()

  return (
    <Dialog open={apiKey !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Copy your API key now</DialogTitle>
          <DialogDescription>
            This is the only time the full key can be displayed. Store it in
            your integration's secret manager.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md border bg-muted p-3 font-mono text-sm break-all">
          {apiKey?.key}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => apiKey && void copy(apiKey.key)}
          >
            {copiedText === apiKey?.key ? <Check /> : <Copy />}
            {copiedText === apiKey?.key ? "Copied" : "Copy key"}
          </Button>
          <Button onClick={onClose}>I've saved it</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ApiKeys
