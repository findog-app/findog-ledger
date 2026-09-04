import { expect, test } from "@playwright/test"

import {
  CategoriesService,
  client,
  LedgersService,
  LoginService,
} from "../src/client"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

async function createCategoryHistoryFixture() {
  client.setConfig({
    baseURL: process.env.VITE_API_URL ?? "http://localhost:8000",
  })
  const token = await LoginService.loginAccessToken({
    formData: {
      username: firstSuperuser,
      password: firstSuperuserPassword,
    },
  })
  client.setConfig({ auth: token.access_token })

  const ledger = await LedgersService.createLedger({
    requestBody: { name: `Category history ${Date.now()}` },
  })
  const group = await CategoriesService.createCategoryGroup({
    ledgerId: ledger.id,
    requestBody: { name: "Utilities" },
  })
  await CategoriesService.createCategory({
    ledgerId: ledger.id,
    requestBody: {
      category_group_id: group.id,
      name: "Water",
      code: "WATR",
      data_source_policy: "hybrid",
    },
  })

  return ledger
}

for (const width of [320, 375, 414]) {
  test(`keeps the Category History chart contained at ${width}px`, async ({
    page,
  }) => {
    const ledger = await createCategoryHistoryFixture()
    await page.setViewportSize({ width, height: 844 })
    await page.goto(`/ledgers/${ledger.id}/analytics`)

    const chart = page.getByTestId("category-history-chart")
    await expect(chart).toBeVisible()
    await expect
      .poll(() =>
        chart.evaluate((element) => element.scrollWidth > element.clientWidth),
      )
      .toBe(true)
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      )
      .toBe(true)

    await chart.evaluate((element) => {
      element.scrollLeft = 100
    })
    await expect
      .poll(() => chart.evaluate((element) => element.scrollLeft))
      .toBeGreaterThan(0)
  })
}
