import { test, expect } from "@playwright/test";
import { setupAPIMocks } from "./helpers/mock-api";

test.describe("Signal Detail Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAPIMocks(page);
    await page.goto("/signals/signal-1");
    await page.waitForSelector("text=Ontario Cybersecurity Wave");
  });

  // ─── Header ───

  test("shows signal name as page heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Ontario Cybersecurity Wave" })).toBeVisible();
  });

  test("shows funding theme and procurement category", async ({ page }) => {
    await expect(page.getByText("Cybersecurity Modernization → IT Security")).toBeVisible();
  });

  test("shows confidence badge", async ({ page }) => {
    await expect(page.getByText("88% Confidence")).toBeVisible();
  });

  test("shows total funding, grant count, and signal strength", async ({ page }) => {
    await expect(page.getByText("Total Funding")).toBeVisible();
    // Use exact match to avoid collisions with other text containing $18.4M
    await expect(page.getByText("$18.4M", { exact: true })).toBeVisible();
    await expect(page.getByText("Grant Count")).toBeVisible();
    await expect(page.getByText("14", { exact: true })).toBeVisible();
    await expect(page.getByText("Signal Strength")).toBeVisible();
    await expect(page.getByText("strong", { exact: true })).toBeVisible();
  });

  // ─── Forecast Timeline ───

  test("shows Forecast Timeline section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Forecast Timeline" })).toBeVisible();
  });

  test("shows Grant Period and Predicted RFP Window labels in timeline", async ({ page }) => {
    await expect(page.getByText("Grant Period")).toBeVisible();
    await expect(page.getByText("Predicted RFP Window")).toBeVisible();
  });

  // ─── Why This Signal ───

  test("shows Why This Signal explanation", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Why This Signal?" })).toBeVisible();
    await expect(page.getByText(/Based on historical analysis/)).toBeVisible();
  });

  // ─── RFP Predictions ───

  test("shows Predicted RFP Opportunities section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Predicted RFP Opportunities" })).toBeVisible();
  });

  test("shows RFP prediction summary", async ({ page }) => {
    await expect(
      page.getByText(/Based on \$18.4M in cybersecurity grants/)
    ).toBeVisible();
  });

  test("shows total estimated RFP value range", async ({ page }) => {
    await expect(page.getByText("Total Estimated RFP Value")).toBeVisible();
    // Use more specific locator to avoid multiple matches
    await expect(page.getByText("$2.8M – $8.3M")).toBeVisible();
  });

  test("shows expected RFP types count", async ({ page }) => {
    await expect(page.getByText("Expected RFP Types")).toBeVisible();
    await expect(page.getByText("2 categories")).toBeVisible();
  });

  test("shows individual RFP predictions with details", async ({ page }) => {
    // First RFP type
    await expect(page.getByText("Penetration Testing & Vulnerability Assessment")).toBeVisible();
    await expect(page.getByText("high likelihood")).toBeVisible();

    // Second RFP type
    await expect(page.getByText("Managed Security Operations Center (SOC)")).toBeVisible();
    await expect(page.getByText("medium likelihood")).toBeVisible();
  });

  test("shows target bidders for RFP predictions", async ({ page }) => {
    await expect(page.getByText("Cybersecurity firms")).toBeVisible();
    await expect(page.getByText("IT consulting firms")).toBeVisible();
  });

  test("shows timeline for RFP predictions", async ({ page }) => {
    await expect(page.getByText("3-6 months")).toBeVisible();
    await expect(page.getByText("6-12 months")).toBeVisible();
  });

  // ─── Supporting Grants Table ───

  test("shows Supporting Grants section with count", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /Supporting Grants/ })).toBeVisible();
  });

  test("supporting grants table has correct headers", async ({ page }) => {
    for (const header of ["Recipient", "Issuer", "Amount", "Date", "Region", "Theme"]) {
      await expect(page.getByRole("columnheader", { name: header })).toBeVisible();
    }
  });

  test("supporting grants table shows grant data", async ({ page }) => {
    await expect(page.getByRole("cell", { name: "CyberSafe Solutions Inc." })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Department of National Defence" })).toBeVisible();
  });

  // ─── Navigation ───

  test("Back to Dashboard link works", async ({ page }) => {
    const backLink = page.getByRole("link", { name: "← Back to Dashboard" });
    await expect(backLink).toBeVisible();
    await backLink.click();
    await expect(page).toHaveURL("/");
  });

  // ─── Edge: Signal Not Found ───

  test("shows not found message for invalid signal", async ({ page }) => {
    await page.route(/\/api\/signals\/nonexistent/, (route) => {
      route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Signal not found" }),
      });
    });
    await page.goto("/signals/nonexistent");
    await expect(page.getByText("Signal not found")).toBeVisible();
  });
});
