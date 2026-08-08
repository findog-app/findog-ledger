import {
  useMutation,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query"
import { Check, UserPlus } from "lucide-react"
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
import { Input } from "@/components/ui/input"
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
                  <Badge variant="outline" className="shrink-0">
                    {member.role === "owner" && <Check />}
                    {member.role}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default LedgerSharing
