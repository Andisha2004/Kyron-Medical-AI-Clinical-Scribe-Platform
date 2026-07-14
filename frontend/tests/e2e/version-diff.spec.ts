import { expect, test } from "@playwright/test";

import { loginAs } from "./support/app";
import { prepareDemoData } from "./support/backend";

test.beforeAll(() => {
  prepareDemoData();
});

test("provider can compare two note versions and see additions and removals", async ({ page }) => {
  await loginAs(page, "provider");

  await page.getByTestId("new-encounter-link").click();
  await expect(page.getByTestId("new-encounter-form")).toBeVisible();

  const suffix = Date.now().toString();
  await page.getByTestId("patient-first-name-input").fill(`Taylor${suffix}`);
  await page.getByTestId("patient-last-name-input").fill("Diff");
  await page.getByTestId("patient-dob-input").fill("1991-02-03");
  await page.getByTestId("create-encounter-button").click();

  await page.waitForURL("**/provider/encounters/**");

  await page.getByTestId("subjective-input").fill("Version one subjective content.");
  await page.getByTestId("objective-input").fill("Version one objective content.");
  await page.getByTestId("assessment-input").fill("Version one assessment content.");
  await page.getByTestId("plan-input").fill("Version one plan content.");

  await page.getByTestId("save-note-button").click();
  await expect(page.getByTestId("selected-version-heading")).toContainText("Version 1 details", {
    timeout: 15_000,
  });

  await page.getByTestId("subjective-input").fill("Version two subjective content.");
  await page.getByTestId("objective-input").fill("Version two objective content.");
  await page.getByTestId("assessment-input").fill("Version two assessment content.");
  await page.getByTestId("plan-input").fill("Version two plan content.");

  await page.getByTestId("save-note-button").click();
  await expect(page.getByRole("button", { name: /Version 2/ })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: /Version 2/ }).click();
  await expect(page.getByTestId("selected-version-heading")).toContainText("Version 2 details");

  await expect(page.getByTestId("version-history-panel")).toBeVisible();
  await expect(page.getByTestId("version-compare-select")).toHaveValue(/.+/);

  await expect(page.getByTestId("version-diff-subjective-removed")).toContainText(
    "Version one subjective content.",
  );
  await expect(page.getByTestId("version-diff-subjective-added")).toContainText(
    "Version two subjective content.",
  );
  await expect(page.getByTestId("version-diff-objective-removed")).toContainText(
    "Version one objective content.",
  );
  await expect(page.getByTestId("version-diff-objective-added")).toContainText(
    "Version two objective content.",
  );
  await expect(page.getByTestId("version-diff-assessment-removed")).toContainText(
    "Version one assessment content.",
  );
  await expect(page.getByTestId("version-diff-assessment-added")).toContainText(
    "Version two assessment content.",
  );
  await expect(page.getByTestId("version-diff-plan-removed")).toContainText(
    "Version one plan content.",
  );
  await expect(page.getByTestId("version-diff-plan-added")).toContainText(
    "Version two plan content.",
  );

  await page.getByRole("button", { name: "Version 1" }).click();
  await expect(page.getByTestId("selected-version-heading")).toContainText("Version 1 details");
  await expect(page.getByTestId("selected-version-subjective")).toContainText(
    "Version one subjective content.",
  );
  await expect(page.getByTestId("selected-version-subjective")).not.toContainText(
    "Version two subjective content.",
  );
});
