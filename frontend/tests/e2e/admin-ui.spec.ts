import { expect, test } from "@playwright/test";

import { loginAs } from "./support/app";
import { prepareDemoData } from "./support/backend";

test.beforeAll(() => {
  prepareDemoData();
});

test("admin can create a provider and manage templates from the UI", async ({ page }) => {
  await loginAs(page, "admin");

  const suffix = Date.now().toString();

  await page.goto("/admin/providers");
  await page.getByTestId("provider-first-name-input").fill("E2E");
  await page.getByTestId("provider-last-name-input").fill("Provider");
  await page.getByTestId("provider-email-input").fill(`e2e-provider-${suffix}@kyron-demo.com`);
  await page.getByTestId("provider-specialty-input").fill("Family Medicine");
  await page.getByTestId("provider-password-input").fill("DemoPass123!");
  await page.getByTestId("create-provider-button").click();

  await expect(page.getByTestId("admin-provider-table")).toContainText(
    `e2e-provider-${suffix}@kyron-demo.com`,
    {
      timeout: 10_000,
    },
  );

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Deactivate" }).first().click();

  await page.goto("/admin/templates");
  await page.getByTestId("new-template-button").click();
  await page.getByTestId("template-name-input").fill(`E2E Template ${suffix}`);
  await page.getByTestId("template-description-input").fill("Template created by Playwright.");
  await page
    .getByTestId("template-section-subjective")
    .fill("Capture history in a concise clinical style.");
  await page.getByTestId("template-section-objective").fill("Only use documented findings.");
  await page.getByTestId("template-section-assessment").fill("Summarize the leading diagnosis.");
  await page.getByTestId("template-section-plan").fill("Keep the plan clear and action oriented.");
  await page.getByTestId("template-section-general").fill("Use dense but readable clinical prose.");
  await page.getByTestId("save-template-button").click();

  await expect(page.getByTestId("template-list")).toContainText(`E2E Template ${suffix}`, {
    timeout: 10_000,
  });
});

test("admin encounter filters and read-only review load successfully", async ({ page }) => {
  await loginAs(page, "admin");
  await page.goto("/admin/encounters");

  await expect(page.getByTestId("admin-encounters-table")).toBeVisible();
  await page.getByTestId("encounter-provider-filter").selectOption({ label: "Maya Chen" });
  await page.getByRole("link", { name: "Read-only view" }).first().click();

  await expect(page.getByText(/Read-only admin review/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Encounter details" })).toBeVisible();
});
