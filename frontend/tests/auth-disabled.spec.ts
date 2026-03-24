import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("Public signup page is not available", async ({ page }) => {
  await page.goto("/signup")

  await expect(page.getByTestId("not-found")).toBeVisible()
})

test("Demo items page is not available", async ({ page }) => {
  await page.goto("/items")

  await expect(page.getByTestId("not-found")).toBeVisible()
})
