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

test("shows the empty category custom-data history", async ({ page }) => {
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
    name: `View custom data for ${categoryName}`,
  })
  await customDataButton.click()
  await expect(
    page.getByText(
      "No custom data records have been saved for this category yet.",
    ),
  ).toBeVisible()
  await page.getByRole("button", { name: "Close", exact: true }).click()

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
  await expect(
    page.getByText(
      "No custom data records have been saved for this category yet.",
    ),
  ).toBeVisible()
})

test("filters the category table and moves a category between groups", async ({
  page,
}) => {
  const ledgerName = uniqueName("Category table")
  const firstGroup = uniqueName("Housing")
  const secondGroup = uniqueName("Utilities")
  const categoryName = uniqueName("Rent")

  await page.goto("/ledgers")
  await page.getByRole("button", { name: "New ledger" }).click()
  await page.getByLabel("Name").fill(ledgerName)
  await page.getByRole("button", { name: "Create ledger" }).click()
  await page.getByRole("link", { name: ledgerName }).click()
  await page.getByRole("link", { name: "Categories" }).click()

  for (const groupName of [firstGroup, secondGroup]) {
    await page.getByRole("button", { name: "New group" }).click()
    await page.getByLabel("Name").fill(groupName)
    await page.getByRole("button", { name: "Create group" }).click()
  }

  await page.getByRole("button", { name: "New category" }).click()
  await page.getByLabel("Group").click()
  await page.getByRole("option", { name: firstGroup }).click()
  await page.getByLabel("Name").fill(categoryName)
  await page.getByLabel("Code").fill("RENT")
  await page.getByRole("button", { name: "Create category" }).click()

  await page.getByPlaceholder("Search name or code").fill("RENT")
  await expect(page.getByText(categoryName, { exact: true })).toBeVisible()
  await expect(page.getByText(firstGroup, { exact: true })).toBeVisible()

  await page.getByRole("button", { name: `Edit ${categoryName}` }).click()
  await page.getByLabel("Group").click()
  await page.getByRole("option", { name: secondGroup }).click()
  await page.getByRole("button", { name: "Save changes" }).click()
  await expect(page.getByText("Category updated")).toBeVisible()
  await expect(page.getByText(secondGroup, { exact: true })).toBeVisible()
})
