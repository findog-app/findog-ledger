import { LoginService, OpenAPI, UsersService } from "../../src/client"
import { firstSuperuser, firstSuperuserPassword } from "../config"

OpenAPI.BASE = `${process.env.VITE_API_URL}`

export const createUser = async ({
  email,
  password,
}: {
  email: string
  password: string
}) => {
  const token = await LoginService.loginAccessToken({
    formData: {
      username: firstSuperuser,
      password: firstSuperuserPassword,
    },
  })

  OpenAPI.TOKEN = token.access_token

  return await UsersService.createUser({
    requestBody: {
      email,
      password,
      is_active: true,
      is_superuser: false,
      full_name: "Test User",
    },
  })
}
