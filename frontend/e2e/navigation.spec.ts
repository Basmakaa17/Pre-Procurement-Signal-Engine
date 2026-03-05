import { test, expect } from "@playwright/test";
import { setupAPIMocks } from "./helpers/mock-api";

test.describe("Navigation & Pipeline Controls", () => {
  test.beforeEach(async ({ page }) => {
    await setupAPIMocks(page);
  });

  // ─── Navigation Bar ───

  test("navigation bar is hidden on landing page", async ({ page }) => {
    await page.goto("/");
    // The inner-page nav should not be visible on the landing page
    await expect(page.locator("nav.sticky")).not.toBeVisible();
  });

  test("navigation bar is visible on dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("nav.sticky")).toBeVisible();
  });

  test("shows Publicus branding in nav", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("PUBLICUS")).toBeVisible();
    await expect(page.getByText("Signal Engine")).toBeVisible();
  });

  test("nav has Dashboard link", async ({ page }) => {
    await page.goto("/dashboard");
    const dashboardLink = page.locator("nav").getByRole("link", { name: "Dashboard" });
    await expect(dashboardLink).toBeVisible();
  });

  test("nav has Grants link", async ({ page }) => {
    await page.goto("/dashboard");
    const grantsLink = page.locator("nav").getByRole("link", { name: "Grants" });
    await expect(grantsLink).toBeVisible();
  });

  test("Dashboard link has active style on dashboard page", async ({ page }) => {
    await page.goto("/dashboard");
    const dashboardLink = page.locator("nav").getByRole("link", { name: "Dashboard" });
    await expect(dashboardLink).toHaveClass(/text-\[#634086\]/);
  });

  test("Grants link has active style on grants page", async ({ page }) => {
    await page.goto("/grants");
    const grantsLink = page.locator("nav").getByRole("link", { name: "Grants" });
    await expect(grantsLink).toHaveClass(/text-\[#634086\]/);
  });

  test("clicking Dashboard link navigates to /dashboard", async ({ page }) => {
    await page.goto("/grants");
    await page.locator("nav").getByRole("link", { name: "Dashboard" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("clicking Grants link navigates to /grants", async ({ page }) => {
    await page.goto("/dashboard");
    await page.locator("nav").getByRole("link", { name: "Grants" }).click();
    await expect(page).toHaveURL(/\/grants/);
  });

  test("clicking logo navigates to landing page", async ({ page }) => {
    await page.goto("/dashboard");
    await page.locator("nav").getByRole("link").first().click();
    await expect(page).toHaveURL("/");
  });

  // ─── Pipeline Controls ───

  test("Run Pipeline button is visible", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: "Run Pipeline" })).toBeVisible();
  });

  test("Run Pipeline button triggers pipeline and shows toast", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Run Pipeline" }).click();
    // Should show "Running..." while pipeline is in progress
    await expect(page.getByText("Running...")).toBeVisible();
    // Should show success toast
    await expect(page.getByText("Pipeline started successfully")).toBeVisible();
  });

  test("Run Pipeline button is disabled while pipeline is running", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Run Pipeline" }).click();
    // Should be disabled immediately
    const runningBtn = page.getByRole("button", { name: "Running..." });
    await expect(runningBtn).toBeDisabled();
  });

  test("Pipeline status indicator appears after triggering pipeline", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Run Pipeline" }).click();
    // Wait for the pipeline status indicator to appear
    await expect(page.getByText("Pipeline Status")).toBeVisible();
  });

  test("Pipeline status indicator shows stats", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Run Pipeline" }).click();
    // Wait for status to update
    await page.waitForTimeout(2500); // Wait for polling
    await expect(page.getByText("Fetched")).toBeVisible();
    await expect(page.getByText("Cleaned")).toBeVisible();
    await expect(page.getByText("Classified")).toBeVisible();
  });

  // ─── Last Updated ───

  test("shows last updated timestamp in nav", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText(/Last updated:/)).toBeVisible();
  });
});
