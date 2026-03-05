import { test, expect } from "@playwright/test";
import { setupAPIMocks } from "./helpers/mock-api";

test.describe("Dashboard Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAPIMocks(page);
    await page.goto("/dashboard");
    // Wait for data to load
    await page.waitForSelector("text=Total Grants Processed");
  });

  // ─── Stats Bar ───

  test("displays all four stats cards", async ({ page }) => {
    await expect(page.getByText("Total Grants Processed")).toBeVisible();
    await expect(page.getByText("Total Funding Tracked")).toBeVisible();
    await expect(page.getByText("Active Signals")).toBeVisible();
    // Use exact match to avoid collision with the table header
    await expect(page.locator(".text-xs.text-gray-500.mb-1").filter({ hasText: "RFP Signal (Procurement)" })).toBeVisible();
  });

  test("shows correct total grants count", async ({ page }) => {
    // MOCK_OVERVIEW.grants.total = 150
    await expect(page.getByText("150")).toBeVisible();
  });

  test("shows active signals count with strength breakdown", async ({ page }) => {
    // Use exact match for "8" to avoid collision with other numbers
    await expect(page.getByText("8", { exact: true })).toBeVisible();
    await expect(page.getByText("3 strong, 3 moderate, 2 weak")).toBeVisible();
  });

  test("shows procurement signal distribution", async ({ page }) => {
    // MOCK_OVERVIEW: high=12, medium=33, low=45, noise=55
    // Actionable = high + medium = 12 + 33 = 45
    await expect(page.getByText("45 Actionable")).toBeVisible();
    await expect(page.getByText(/12 high, 33 medium, 45 low, 55 noise/)).toBeVisible();
  });

  // ─── Signal Feed ───

  test("shows Procurement Signals heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Procurement Signals" })).toBeVisible();
  });

  test("displays signal filter buttons", async ({ page }) => {
    for (const label of ["All", "Strong", "Moderate", "Weak"]) {
      await expect(page.getByRole("button", { name: label })).toBeVisible();
    }
  });

  test("signal cards are rendered from mocked API", async ({ page }) => {
    // Signals may take time to load - wait for any signal card content
    await expect(page.getByText("Ontario Cybersecurity Wave").first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Federal AI Modernization").first()).toBeVisible();
  });

  test("signal card shows procurement category", async ({ page }) => {
    // Wait for signal cards
    await page.waitForSelector("text=Likely Procurement:", { timeout: 15000 });
    await expect(page.getByText("Likely Procurement:").first()).toBeVisible();
  });

  test("signal filter buttons change active state", async ({ page }) => {
    const strongBtn = page.getByRole("button", { name: "Strong" });
    await strongBtn.click();
    // After clicking, the button should have the active class
    await expect(strongBtn).toHaveClass(/bg-\[#634086\]/);
  });

  test("region filter dropdown is present", async ({ page }) => {
    const select = page.locator("select");
    await expect(select.first()).toBeVisible();
    await expect(select.first()).toContainText("All Regions");
  });

  // ─── Sector Momentum ───

  test("shows Sector Momentum section", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Sector Momentum" })).toBeVisible();
  });

  test("displays theme bars in Sector Momentum", async ({ page }) => {
    // Use the sector momentum section specifically to avoid collision with table cells
    const sectorSection = page.locator("section.col-span-3");
    await expect(sectorSection.getByText("Cybersecurity Modernization")).toBeVisible();
    await expect(sectorSection.getByText("Healthcare Digitization")).toBeVisible();
  });

  // ─── Recent Grants Table ───

  test("shows Recent Grants heading with View All link", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Recent Grants" })).toBeVisible();
    const viewAll = page.getByRole("link", { name: "View All →" });
    await expect(viewAll).toBeVisible();
    await expect(viewAll).toHaveAttribute("href", "/grants");
  });

  test("grants table has correct headers", async ({ page }) => {
    for (const header of ["Source", "Recipient", "Issuer", "Amount", "Date", "Theme", "RFP Signal", "Relevance"]) {
      await expect(page.getByRole("columnheader", { name: header })).toBeVisible();
    }
  });

  test("grants table shows grant data", async ({ page }) => {
    await expect(page.getByRole("cell", { name: "CyberSafe Solutions Inc." })).toBeVisible();
    await expect(page.getByRole("cell", { name: "open_canada" }).first()).toBeVisible();
  });

  test("grants table shows business relevance badges", async ({ page }) => {
    // Should show "High" badge for the first grant
    const highBadge = page.locator("td span").filter({ hasText: /High/ }).first();
    await expect(highBadge).toBeVisible();
  });

  // ─── Navigation ───

  test("View All link navigates to grants page", async ({ page }) => {
    await page.getByRole("link", { name: "View All →" }).click();
    await expect(page).toHaveURL(/\/grants/);
  });

  test("View Full Signal link on card is present", async ({ page }) => {
    // Wait for signal cards first
    await page.waitForSelector("text=View Full Signal", { timeout: 15000 });
    const link = page.getByRole("link", { name: "View Full Signal →" }).first();
    await expect(link).toBeVisible();
  });
});
