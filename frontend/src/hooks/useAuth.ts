import { useMutation, useQuery } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { useEffect } from "react"

import {
  type Body_login_login_access_token as AccessToken,
  ApiError,
  LedgersService,
  LoginService,
  type UserPublic,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

const isCurrentUserSessionError = (error: unknown) =>
  error instanceof ApiError &&
  [400, 401, 403, 404].includes(error.response?.status ?? 0)

const useAuth = () => {
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()

  const { data: user, error: currentUserError } = useQuery<
    UserPublic | null,
    Error
  >({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
    retry: (failureCount, error) =>
      !isCurrentUserSessionError(error) && failureCount < 3,
  })

  useEffect(() => {
    if (!isCurrentUserSessionError(currentUserError)) return
    localStorage.removeItem("access_token")
    window.location.replace("/login")
  }, [currentUserError])

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: async () => {
      try {
        const ledgers = await LedgersService.readLedgers()
        const lastLedgerId = localStorage.getItem("last-ledger-id")
        const activeLedger = ledgers.data.find(
          (ledger) => ledger.id === lastLedgerId,
        )
        const ledger = activeLedger ?? ledgers.data[0]

        if (ledger) {
          navigate({
            to: "/ledgers/$ledgerId",
            params: { ledgerId: ledger.id },
          })
          return
        }
      } catch {
        // The session is valid even when the optional landing lookup fails.
      }

      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    navigate({ to: "/login" })
  }

  return {
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
