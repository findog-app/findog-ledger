import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { Check, Trash2, UserPlus } from "lucide-react"
import { useState } from "react"

import {
  type LedgerAccessRole,
  type LedgerShare,
  LedgersService,
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
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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

const shareRoles: Array<{ value: LedgerAccessRole; label: string }> = [
  { value: "viewer", label: "Viewer" },
  { value: "editor", label: "Editor" },
]

export function LedgerSharing({ ledgerId }: { ledgerId: string }) {
  const [email, setEmail] = useState("")
  const [role, setRole] = useState<LedgerAccessRole>("viewer")
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const { data: members } = useSuspenseQuery({
    queryFn: () => LedgersService.readLedgerMembers({ ledgerId }),
    queryKey: ["ledger-members", ledgerId],
  })
  const shareMutation = useMutation({
    mutationFn: (requestBody: LedgerShare) =>
      LedgersService.shareLedger({ ledgerId, requestBody }),
    onSuccess: () => {
      showSuccessToast("Ledger shared successfully")
      setEmail("")
      void queryClient.invalidateQueries({
        queryKey: ["ledger-members", ledgerId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })
  const updateMutation = useMutation({
    mutationFn: ({
      userId,
      role,
    }: {
      userId: string
      role: LedgerAccessRole
    }) =>
      LedgersService.updateLedgerMember({
        ledgerId,
        userId,
        requestBody: { role },
      }),
    onSuccess: () => {
      showSuccessToast("Ledger access updated")
      void queryClient.invalidateQueries({
        queryKey: ["ledger-members", ledgerId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })
  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      LedgersService.removeLedgerMember({ ledgerId, userId }),
    onSuccess: () => {
      showSuccessToast("Ledger access removed")
      void queryClient.invalidateQueries({
        queryKey: ["ledger-members", ledgerId],
      })
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleShare = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!email.trim()) return
    shareMutation.mutate({ email: email.trim(), role })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserPlus className="size-5" />
          Ledger access
        </CardTitle>
        <CardDescription>
          Share this ledger with another provisioned user and choose their
          access level.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form
          className="grid gap-3 sm:grid-cols-[1fr_auto_auto]"
          onSubmit={handleShare}
        >
          <Input
            placeholder="user@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-label="User email"
          />
          <Select
            value={role}
            onValueChange={(value) => setRole(value as LedgerAccessRole)}
          >
            <SelectTrigger className="w-full sm:w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {shareRoles.map((shareRole) => (
                <SelectItem key={shareRole.value} value={shareRole.value}>
                  {shareRole.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="submit"
            disabled={!email.trim() || shareMutation.isPending}
          >
            Share ledger
          </Button>
        </form>

        <div className="space-y-2">
          <p className="text-sm font-medium">Current members</p>
          {members.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">No members yet.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {members.data.map((member) => (
                <div
                  key={member.user_id}
                  className="flex items-center justify-between gap-4 px-3 py-3 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">
                      {member.full_name || member.email}
                    </p>
                    {member.full_name && (
                      <p className="truncate text-xs text-muted-foreground">
                        {member.email}
                      </p>
                    )}
                  </div>
                  {member.role === "owner" ? (
                    <Badge variant="outline" className="shrink-0">
                      <Check />
                      owner
                    </Badge>
                  ) : (
                    <div className="flex shrink-0 items-center gap-2">
                      <Select
                        value={member.role}
                        onValueChange={(value) =>
                          updateMutation.mutate({
                            userId: member.user_id,
                            role: value as LedgerAccessRole,
                          })
                        }
                        disabled={updateMutation.isPending}
                      >
                        <SelectTrigger className="w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {shareRoles.map((shareRole) => (
                            <SelectItem
                              key={shareRole.value}
                              value={shareRole.value}
                            >
                              {shareRole.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <RemoveMemberDialog
                        email={member.email}
                        isPending={removeMutation.isPending}
                        onConfirm={() => removeMutation.mutate(member.user_id)}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function RemoveMemberDialog({
  email,
  isPending,
  onConfirm,
}: {
  email: string
  isPending: boolean
  onConfirm: () => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Remove ${email}`}>
          <Trash2 />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Remove ledger access?</DialogTitle>
          <DialogDescription>
            {email} will no longer be able to access this ledger.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            loading={isPending}
            onClick={() => {
              onConfirm()
              setOpen(false)
            }}
          >
            Remove access
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default LedgerSharing
