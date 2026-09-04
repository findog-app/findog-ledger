import type { AxiosResponse } from "axios"
import * as generated from "./client/sdk.gen"

export { AxiosError as ApiError } from "axios"
export { client } from "./client/client.gen"
export type { BodyLoginLoginAccessToken as Body_login_login_access_token } from "./client/types.gen"
export * from "./client/types.gen"

type LegacyOptions = Record<string, unknown> | undefined
type SdkFunction = (...args: any[]) => Promise<unknown>
type ResponseBody<T> = T extends { data: infer Body }
  ? NonNullable<Body>
  : never

const snakeCase = (key: string) =>
  key
    .replace(/^_/, "")
    .replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)

const request =
  <Fn extends SdkFunction>(fn: Fn) =>
  async (
    options?: LegacyOptions,
  ): Promise<ResponseBody<Awaited<ReturnType<Fn>>>> => {
    const { formData, requestBody, ...params } = options ?? {}
    const fields = Object.fromEntries(
      Object.entries(params).map(([key, value]) => [snakeCase(key), value]),
    )
    const response = await (fn as (options: unknown) => Promise<AxiosResponse>)(
      {
        body: requestBody ?? formData,
        path: fields,
        query: fields,
        throwOnError: true,
      },
    )
    return response.data as ResponseBody<Awaited<ReturnType<Fn>>>
  }

export const AnalyticsService = {
  readCategoryAmountHistory: request(
    generated.AnalyticsService.readCategoryAmountHistory,
  ),
  readObligationPeriodTotals: request(
    generated.AnalyticsService.readObligationPeriodTotals,
  ),
  readPeriodPaymentSummary: request(
    generated.AnalyticsService.readPeriodPaymentSummary,
  ),
  readRemainingPeriodCashflow: request(
    generated.AnalyticsService.readRemainingPeriodCashflow,
  ),
}
export const CategoriesService = {
  archiveCategory: request(generated.CategoriesService.archiveCategory),
  archiveCategoryGroup: request(
    generated.CategoriesService.archiveCategoryGroup,
  ),
  createCategory: request(generated.CategoriesService.createCategory),
  createCategoryDataSchema: request(
    generated.CategoriesService.createCategoryDataSchema,
  ),
  createCategoryGroup: request(generated.CategoriesService.createCategoryGroup),
  readCategories: request(generated.CategoriesService.readCategories),
  readCategoryDataRecords: request(
    generated.CategoriesService.readCategoryDataRecords,
  ),
  readCategoryDataSchema: request(
    generated.CategoriesService.readCategoryDataSchema,
  ),
  readCategoryGroups: request(generated.CategoriesService.readCategoryGroups),
  restoreCategory: request(generated.CategoriesService.restoreCategory),
  updateCategory: request(generated.CategoriesService.updateCategory),
  updateCategoryGroup: request(generated.CategoriesService.updateCategoryGroup),
}
export const LedgersService = {
  createApiKey: request(generated.LedgersService.createApiKey),
  createLedger: request(generated.LedgersService.createLedger),
  deleteAllCategories: request(generated.LedgersService.deleteAllCategories),
  deleteAllObligations: request(generated.LedgersService.deleteAllObligations),
  readApiKeys: request(generated.LedgersService.readApiKeys),
  readLedger: request(generated.LedgersService.readLedger),
  readLedgerMembers: request(generated.LedgersService.readLedgerMembers),
  readLedgers: request(generated.LedgersService.readLedgers),
  removeLedgerMember: request(generated.LedgersService.removeLedgerMember),
  revokeApiKey: request(generated.LedgersService.revokeApiKey),
  shareLedger: request(generated.LedgersService.shareLedger),
  updateLedger: request(generated.LedgersService.updateLedger),
  updateLedgerMember: request(generated.LedgersService.updateLedgerMember),
}
export const LoginService = {
  loginAccessToken: request(generated.LoginService.loginAccessToken),
  recoverPassword: request(generated.LoginService.recoverPassword),
  resetPassword: request(generated.LoginService.resetPassword),
}
export const ObligationsService = {
  addObligationComponent: request(
    generated.ObligationsService.addObligationComponent,
  ),
  cancelObligation: request(generated.ObligationsService.cancelObligation),
  createObligation: request(generated.ObligationsService.createObligation),
  markObligationPaid: request(generated.ObligationsService.markObligationPaid),
  markObligationReady: request(
    generated.ObligationsService.markObligationReady,
  ),
  readObligation: request(generated.ObligationsService.readObligation),
  readObligationComponents: request(
    generated.ObligationsService.readObligationComponents,
  ),
  readObligations: request(generated.ObligationsService.readObligations),
  removeObligationComponent: request(
    generated.ObligationsService.removeObligationComponent,
  ),
  reopenObligation: request(generated.ObligationsService.reopenObligation),
  updateObligation: request(generated.ObligationsService.updateObligation),
  updateObligationComponent: request(
    generated.ObligationsService.updateObligationComponent,
  ),
}
export const SystemRunsService = {
  readSystemRunTasks: request(
    generated.SystemRunsService.runsReadSystemRunTasks,
  ),
  readSystemRuns: request(generated.SystemRunsService.runsReadSystemRuns),
  startSystemRun: request(generated.SystemRunsService.runsStartSystemRun),
}
export const UsersService = {
  createUser: request(generated.UsersService.createUser),
  deleteUser: request(generated.UsersService.deleteUser),
  deleteUserMe: request(generated.UsersService.deleteUserMe),
  readUserMe: request(generated.UsersService.readUserMe),
  readUsers: request(generated.UsersService.readUsers),
  updatePasswordMe: request(generated.UsersService.updatePasswordMe),
  updateUser: request(generated.UsersService.updateUser),
  updateUserMe: request(generated.UsersService.updateUserMe),
}
