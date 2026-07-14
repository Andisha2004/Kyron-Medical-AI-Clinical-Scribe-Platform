import { test, expect } from "@playwright/test";

import { loginAs } from "./support/app";
import { prepareDemoData } from "./support/backend";

test.beforeAll(() => {
  prepareDemoData();
});

test("provider login redirects to provider dashboard", async ({ page }) => {
  await loginAs(page, "provider");
  await expect(page.getByTestId("provider-encounter-list")).toBeVisible();
});

test("admin login redirects to admin dashboard", async ({ page }) => {
  await loginAs(page, "admin");
  await expect(page.getByRole("heading", { name: "Recent encounters" })).toBeVisible();
});

test("provider cannot stay on admin route", async ({ page }) => {
  await page.goto("/login?next=/admin");
  await page.getByLabel("Email address").fill("provider1@kyron-demo.com");
  await page.getByLabel("Password").fill("DemoPass123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.waitForURL("**/provider");
  await expect(page.getByRole("heading", { name: "Provider dashboard" })).toBeVisible();
});
