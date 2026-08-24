import { expect, test } from "@playwright/test"

function uniqueName(prefix: string) {
  return `${prefix} ${Math.random().toString(36).slice(2, 8)}`
}

test("manages category custom fields with the builder", async ({ page }) => {
  const ledgerName = uniqueName("Custom fields")
  const groupName = uniqueName("Utilities")
  const categoryName = uniqueName("Electricity")

  await page.goto("/ledgers")
  await page.getByRole("button", { name: "New ledger" }).click()
  await page.getByLabel("Name").fill(ledgerName)
  await page.getByRole("button", { name: "Create ledger" }).click()
  await expect(page.getByText("Ledger created successfully")).toBeVisible()
  await page.getByRole("link", { name: ledgerName }).click()

  await page.getByRole("link", { name: "Categories" }).click()
  await page.getByRole("button", { name: "New group" }).click()
  await page.getByLabel("Name").fill(groupName)
  await page.getByRole("button", { name: "Create group" }).click()
  await expect(page.getByText("Category group created")).toBeVisible()

  await page.getByRole("button", { name: "New category" }).click()
  await page.getByLabel("Group").click()
  await page.getByRole("option", { name: groupName }).click()
  await page.getByLabel("Name").fill(categoryName)
  await page.getByLabel("Code").fill("ELEC")
  await page.getByRole("button", { name: "Create category" }).click()
  await expect(page.getByText("Category created")).toBeVisible()

  const customFieldsButton = page.getByRole("button", {
    name: `Manage custom fields for ${categoryName}`,
  })
  await customFieldsButton.click()
  await page.getByRole("button", { name: "Add field" }).click()
  await page.getByLabel("Field name").fill("meter_reading_kwh")
  await page.getByLabel("Label").fill("Meter reading")
  await page.getByRole("button", { name: "Save custom fields" }).click()
  await expect(
    page.getByText("Custom fields saved as schema version 1"),
  ).toBeVisible()

  await customFieldsButton.click()
  await expect(page.getByDisplayValue("meter_reading_kwh")).toBeVisible()
  await page.getByLabel("Field name").fill("current_reading_kwh")
  await page.getByRole("button", { name: "Save custom fields" }).click()
  await expect(
    page.getByText("Custom fields saved as schema version 2"),
  ).toBeVisible()

  await customFieldsButton.click()
  await page.getByRole("button", { name: "Remove" }).click()
  await expect(page.getByText("No custom fields configured yet.")).toBeVisible()
  await page.getByRole("button", { name: "Save custom fields" }).click()
  await expect(
    page.getByText("Custom fields saved as schema version 3"),
  ).toBeVisible()
})
