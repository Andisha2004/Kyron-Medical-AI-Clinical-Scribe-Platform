import { expect, test } from "@playwright/test";

import { loginAs } from "./support/app";
import { prepareDemoData } from "./support/backend";
import { installSpeechAndMediaMocks } from "./support/browser-mocks";

test.beforeAll(() => {
  prepareDemoData();
});

test("dictation UI handles microphone denial gracefully", async ({ page }) => {
  await installSpeechAndMediaMocks(page, { microphone: "denied" });
  await loginAs(page, "provider");
  await page.goto("/provider/encounters/new");

  const suffix = `${Date.now()}-denied`;
  await page.getByTestId("patient-first-name-input").fill(`Jordan${suffix}`);
  await page.getByTestId("patient-last-name-input").fill("Mic");
  await page.getByTestId("patient-dob-input").fill("1990-01-01");
  await page.getByTestId("create-encounter-button").click();
  await page.waitForURL("**/provider/encounters/**");

  await page.getByTestId("dictation-start-button").click();
  await expect(page.getByTestId("dictation-error")).toContainText("Microphone access was denied.", {
    timeout: 10_000,
  });
});

test("dictation UI shows partial and finalized transcript updates", async ({ page }) => {
  await installSpeechAndMediaMocks(page);
  await loginAs(page, "provider");
  await page.goto("/provider/encounters/new");

  const suffix = `${Date.now()}-dictation`;
  await page.getByTestId("patient-first-name-input").fill(`Jordan${suffix}`);
  await page.getByTestId("patient-last-name-input").fill("Dictation");
  await page.getByTestId("patient-dob-input").fill("1990-01-01");
  await page.getByTestId("create-encounter-button").click();
  await page.waitForURL("**/provider/encounters/**");

  await page.getByTestId("dictation-start-button").click();
  await expect(page.getByTestId("dictation-status")).toContainText("listening", {
    timeout: 10_000,
  });

  await page.evaluate(() => {
    (
      window as typeof window & { __mockSpeech: { emitInterim: (text: string) => void } }
    ).__mockSpeech.emitInterim("patient reports worsening knee pain");
  });
  await expect(page.getByTestId("partial-transcript")).toContainText(
    "patient reports worsening knee pain",
  );

  await page.evaluate(() => {
    (
      window as typeof window & { __mockSpeech: { emitFinal: (text: string) => void } }
    ).__mockSpeech.emitFinal("Patient reports worsening knee pain.");
  });
  await expect(page.getByTestId("finalized-segments")).toContainText(
    "Patient reports worsening knee pain.",
    {
      timeout: 10_000,
    },
  );
  await expect(page.getByTestId("transcript-input")).toHaveValue(
    /Patient reports worsening knee pain\./,
    {
      timeout: 10_000,
    },
  );
});

test("voice editing UI applies spoken command and shows assistant response", async ({ page }) => {
  await installSpeechAndMediaMocks(page);
  await loginAs(page, "provider");
  await page.goto("/provider/encounters/new");

  const suffix = `${Date.now()}-voice`;
  await page.getByTestId("patient-first-name-input").fill(`Jordan${suffix}`);
  await page.getByTestId("patient-last-name-input").fill("Voice");
  await page.getByTestId("patient-dob-input").fill("1990-01-01");
  await page.getByTestId("create-encounter-button").click();
  await page.waitForURL("**/provider/encounters/**");

  await page.getByTestId("voice-start-button").click();
  await expect(page.getByTestId("voice-status")).toContainText("Listening now.", {
    timeout: 10_000,
  });

  await page.evaluate(() => {
    (
      window as typeof window & { __mockSpeech: { emitFinal: (text: string) => void } }
    ).__mockSpeech.emitFinal("Add that the patient denies fever.");
  });

  await expect(page.getByTestId("voice-assistant-response")).toContainText("I added that", {
    timeout: 10_000,
  });
  await expect(page.getByTestId("subjective-input")).toHaveValue(/Patient denies fever\./, {
    timeout: 10_000,
  });
});
