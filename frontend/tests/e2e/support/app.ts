import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export async function loginAs(page: Page, role: "provider" | "admin"): Promise<void> {
  await page.goto("/login");

  const credentials =
    role === "admin"
      ? { email: "admin@kyron-demo.com", password: "DemoPass123!" }
      : { email: "provider1@kyron-demo.com", password: "DemoPass123!" };

  await page.getByLabel("Email address").fill(credentials.email);
  await page.getByLabel("Password").fill(credentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.waitForURL(role === "admin" ? "**/admin" : "**/provider");
  await expect(
    page.getByRole("heading", { name: role === "admin" ? "Administration" : "Provider dashboard" }),
  ).toBeVisible();
}
