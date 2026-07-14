import { expect, test } from "@playwright/test";

import { loginAs } from "./support/app";
import { prepareDemoData } from "./support/backend";

test.beforeAll(() => {
  prepareDemoData();
});

test("provider can create an encounter, generate a note, add ICD code, save, and reload", async ({
  page,
}) => {
  await loginAs(page, "provider");

  await page.getByTestId("new-encounter-link").click();
  await expect(page.getByTestId("new-encounter-form")).toBeVisible();

  const suffix = Date.now().toString();
  await page.getByTestId("patient-first-name-input").fill(`Jordan${suffix}`);
  await page.getByTestId("patient-last-name-input").fill("Workflow");
  await page.getByTestId("patient-dob-input").fill("1990-01-01");
  await page.getByTestId("create-encounter-button").click();

  await page.waitForURL("**/provider/encounters/**");
  await expect(page.getByTestId("workspace-live-status")).toContainText(/Draft|Saved/);

  await page
    .getByTestId("transcript-input")
    .fill("Patient reports chronic right knee pain on stairs and denies fever.");
  await page.getByTestId("observations-input").fill("No exam findings documented yet.");
  await expect(page.getByTestId("workspace-live-status")).toContainText("Saved", {
    timeout: 15_000,
  });

  await page.getByTestId("generate-note-button").click();
  await expect(page.getByTestId("generation-status")).toContainText("Generation complete.", {
    timeout: 15_000,
  });
  await expect(page.getByTestId("subjective-input")).toHaveValue(/right knee pain/i);

  await page.getByTestId("icd-search-input").fill("right knee osteoarthritis");
  const addIcdButton = page.getByTestId("add-icd-M17.11");
  await expect(addIcdButton).toBeVisible();
  if (await addIcdButton.isEnabled()) {
    await addIcdButton.click();
  }
  await expect(addIcdButton).toContainText("Added");
  await expect(page.getByRole("button", { name: "Remove" })).toBeVisible();

  await page.getByTestId("save-note-button").click();
  await expect(page.getByTestId("workspace-live-status")).toContainText("Saved", {
    timeout: 15_000,
  });
  await expect(page.getByRole("heading", { name: "Version 1 details" })).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("subjective-input")).toHaveValue(/right knee pain/i);
  await expect(page.getByRole("heading", { name: "Version 1 details" })).toBeVisible();
});
