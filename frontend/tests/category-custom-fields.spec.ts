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
  const createCategoryButton = page.getByRole("button", {
    name: "Create category",
  })
  await createCategoryButton.scrollIntoViewIfNeeded()
  await createCategoryButton.click()
  await expect(page.getByText("Category created")).toBeVisible()

  const customFieldsButton = page.getByRole("button", {
    name: `Manage custom fields for ${categoryName}`,
  })
  await customFieldsButton.click()
  await page.getByRole("button", { name: "Add field" }).click()
  await page.getByLabel("Field name").fill("meter_reading_kwh")
  await page.getByLabel("Label").fill("Meter reading")
  const saveCustomFieldsButton = page.getByRole("button", {
    name: "Save custom fields",
  })
  await saveCustomFieldsButton.scrollIntoViewIfNeeded()
  await saveCustomFieldsButton.click()
  await expect(
    page.getByText("Custom fields saved as schema version 1"),
  ).toBeVisible()

  await customFieldsButton.click()
  await expect(page.getByLabel("Field name")).toHaveValue("meter_reading_kwh")
  await page.getByLabel("Field name").fill("current_reading_kwh")
  await saveCustomFieldsButton.scrollIntoViewIfNeeded()
  await saveCustomFieldsButton.click()
  await expect(
    page.getByText("Custom fields saved as schema version 2"),
  ).toBeVisible()

  await customFieldsButton.click()
  await page.getByRole("button", { name: "Remove" }).click()
  await expect(page.getByText("No custom fields configured yet.")).toBeVisible()
  await saveCustomFieldsButton.scrollIntoViewIfNeeded()
  await saveCustomFieldsButton.click()
  await expect(
    page.getByText("Custom fields saved as schema version 3"),
  ).toBeVisible()
})

test("views and edits category custom data with the active schema", async ({
  page,
}) => {
  const ledgerName = uniqueName("Custom data")
  const groupName = uniqueName("Utilities")
  const categoryName = uniqueName("Electricity")

  await page.goto("/ledgers")
  await page.getByRole("button", { name: "New ledger" }).click()
  await page.getByLabel("Name").fill(ledgerName)
  await page.getByRole("button", { name: "Create ledger" }).click()
  await page.getByRole("link", { name: ledgerName }).click()
  await page.getByRole("link", { name: "Categories" }).click()
  await page.getByRole("button", { name: "New group" }).click()
  await page.getByLabel("Name").fill(groupName)
  await page.getByRole("button", { name: "Create group" }).click()
  await page.getByRole("button", { name: "New category" }).click()
  await page.getByLabel("Group").click()
  await page.getByRole("option", { name: groupName }).click()
  await page.getByLabel("Name").fill(categoryName)
  await page.getByLabel("Code").fill("DATA")
  const createCategoryButton = page.getByRole("button", {
    name: "Create category",
  })
  await createCategoryButton.scrollIntoViewIfNeeded()
  await createCategoryButton.click()

  const customDataButton = page.getByRole("button", {
    name: `Edit custom data for ${categoryName}`,
  })
  await customDataButton.click()
  await expect(
    page.getByText("No custom fields are configured for this category yet."),
  ).toBeVisible()
  await page.getByRole("button", { name: "Close" }).click()

  await page
    .getByRole("button", {
      name: `Manage custom fields for ${categoryName}`,
    })
    .click()
  await page.getByRole("button", { name: "Add field" }).click()
  await page.getByLabel("Field name").fill("meter_reading")
  await page.getByLabel("Label").fill("Meter reading")
  await page.getByRole("checkbox", { name: "Required" }).check()
  await page.getByLabel("Minimum length").fill("1")
  const saveCustomFieldsButton = page.getByRole("button", {
    name: "Save custom fields",
  })
  await saveCustomFieldsButton.scrollIntoViewIfNeeded()
  await saveCustomFieldsButton.click()
  await expect(
    page.getByText("Custom fields saved as schema version 1"),
  ).toBeVisible()

  await customDataButton.click()
  await expect(page.getByText("Schema version 1")).toBeVisible()
  await expect(page.getByText("No saved custom data yet.")).toBeVisible()
  await page.getByLabel("Meter reading").fill("1200")
  await page.getByRole("button", { name: "Save custom data" }).click()
  await expect(page.getByText("Custom data saved")).toBeVisible()

  await customDataButton.click()
  await expect(page.getByLabel("Meter reading")).toHaveValue("1200")
  await expect(page.getByText(/Last updated/)).toBeVisible()
  await page.getByLabel("Meter reading").fill("")
  await page.getByRole("button", { name: "Save custom data" }).click()
  await expect(page.getByText(/should be non-empty/)).toBeVisible()
})
