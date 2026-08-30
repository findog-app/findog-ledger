import { expect, test } from "@playwright/test"

import { LedgersService, LoginService, OpenAPI } from "../src/client"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

async function createLedgerFixture() {
  OpenAPI.BASE = process.env.VITE_API_URL ?? "http://localhost:8000"
  const token = await LoginService.loginAccessToken({
    formData: {
      username: firstSuperuser,
      password: firstSuperuserPassword,
    },
  })
  OpenAPI.TOKEN = token.access_token
  return LedgersService.createLedger({
    requestBody: { name: `System Run ${Date.now()}` },
  })
}

test("confirms a manual-only System Run before sending its selected tasks", async ({
  page,
}) => {
  const ledger = await createLedgerFixture()
  const startedRun = {
    id: "d3c6c679-8e8f-4ee8-a36c-04bc8ca03396",
    status: "success",
    trigger: "manual",
    effective_at: "2026-09-01T00:30:00Z",
    timezone: "UTC",
    business_date: "2026-09-01",
    summary: { succeeded_steps: 1, failed_steps: 0, skipped_steps: 0 },
    error: null,
    started_at: "2026-09-01T00:30:00Z",
    finished_at: "2026-09-01T00:30:01Z",
    steps: [],
  }
  await page.route("**/api/v1/system-runs/tasks", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        { name: "ensure_obligations", mode: "scheduled" },
        { name: "legacy_import", mode: "manual_only" },
      ]),
    }),
  )
  await page.route("**/api/v1/system-runs/", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(startedRun),
      })
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ data: [], count: 0 }),
    })
  })

  await page.goto(`/ledgers/${ledger.id}/system-run`)
  await page.getByLabel("legacy import").check()
  await page.getByRole("button", { name: "Start System Run" }).click()
  await expect(page.getByRole("dialog")).toContainText("Start System Run?")

  const request = page.waitForRequest(
    (candidate) =>
      candidate.url().endsWith("/api/v1/system-runs/") &&
      candidate.method() === "POST",
  )
  await page.getByRole("button", { name: "Start run" }).click()
  await expect(page.getByText("Run history")).toBeVisible()
  expect((await request).postDataJSON()).toEqual({
    task_names: ["legacy_import"],
  })
})
