import { test, expect } from "@playwright/test";
import { setupAPIMocks } from "./helpers/mock-api";

test.describe("Grants Page", () => {
  test.beforeEach(async ({ page }) => {
    await setupAPIMocks(page);
    await page.goto("/grants");
    // Wait for the page to hydrate and data to appear
    await page.waitForSelector("text=Grant Explorer");
  });

  // ─── Page Layout ───

  test("renders page title", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Grant Explorer" })).toBeVisible();
  });

  // ─── Tabs ───

  test("shows Business Relevant and Non-Relevant tabs", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Business Relevant Grants" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Non-Relevant Grants" })).toBeVisible();
  });

  test("Business Relevant tab is active by default", async ({ page }) => {
    const relevantTab = page.getByRole("button", { name: "Business Relevant Grants" });
    await expect(relevantTab).toHaveClass(/text-\[#634086\]/);
  });

  test("switching to Non-Relevant tab changes active state", async ({ page }) => {
    const nonRelevantTab = page.getByRole("button", { name: "Non-Relevant Grants" });
    await nonRelevantTab.click();
    await expect(nonRelevantTab).toHaveClass(/text-\[#634086\]/);
  });

  test("Business Relevant tab shows high/medium relevance grants", async ({ page }) => {
    // On the relevant tab, should show CyberSafe (high) and MedTech (medium)
    await expect(page.getByText("CyberSafe Solutions Inc.")).toBeVisible();
    await expect(page.getByText("MedTech Innovations Ltd.")).toBeVisible();
  });

  test("Non-Relevant tab shows low relevance grants", async ({ page }) => {
    await page.getByRole("button", { name: "Non-Relevant Grants" }).click();
    // Should show the scholarship grant
    await expect(page.getByText("University of Toronto Student")).toBeVisible();
  });

  // ─── Grant Cards ───

  test("grant card shows recipient name", async ({ page }) => {
    await expect(page.getByText("CyberSafe Solutions Inc.")).toBeVisible();
  });

  test("grant card shows issuer", async ({ page }) => {
    await expect(page.getByText("Department of National Defence")).toBeVisible();
  });

  test("grant card shows amount", async ({ page }) => {
    await expect(page.getByText("$2.5M")).toBeVisible();
  });

  test("grant card shows business relevance banner with score", async ({ page }) => {
    // The high relevance card should have a green banner with percentage
    await expect(page.getByText("High Business Relevance (88%)")).toBeVisible();
  });

  test("grant card shows funding theme", async ({ page }) => {
    // Use exact match to avoid collision with filter options
    const themeSpan = page.locator("span.text-xs.font-medium").filter({ hasText: "Cybersecurity Modernization" });
    await expect(themeSpan.first()).toBeVisible();
  });

  test("grant card shows LLM confidence inline", async ({ page }) => {
    await expect(page.getByText("(LLM confidence: 92%)")).toBeVisible();
  });

  test("grant card description can expand and collapse", async ({ page }) => {
    // The description should be truncated initially
    const showMoreBtn = page.getByText("Show more").first();
    if (await showMoreBtn.isVisible()) {
      await showMoreBtn.click();
      await expect(page.getByText("Show less").first()).toBeVisible();
      await page.getByText("Show less").first().click();
      await expect(page.getByText("Show more").first()).toBeVisible();
    }
  });

  // ─── RFP Predictions on Cards ───

  test("grant card shows predicted RFP button for grants with predictions", async ({ page }) => {
    // CyberSafe has 1 predicted RFP
    await expect(page.getByText(/Predicted RFP/)).toBeVisible();
  });

  test("clicking RFP prediction expands details", async ({ page }) => {
    const rfpButton = page.getByText(/Predicted RFP/).first();
    await rfpButton.click();
    // Should show the expanded RFP details
    await expect(page.getByText("Penetration Testing & Vulnerability Assessment")).toBeVisible();
  });

  // ─── Search Bar ───

  test("search bar is visible and functional", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search grants/);
    await expect(searchInput).toBeVisible();
    await searchInput.fill("cybersecurity");
    // Wait for debounce and search results
    await page.waitForTimeout(600);
    await expect(page.getByText("CyberSafe Solutions Inc.")).toBeVisible();
  });

  // ─── Filters Sidebar ───

  test("shows filter controls in sidebar", async ({ page }) => {
    // Use label elements specifically
    await expect(page.locator("label").filter({ hasText: "Source" })).toBeVisible();
    await expect(page.locator("label").filter({ hasText: "Region" })).toBeVisible();
    await expect(page.locator("label").filter({ hasText: "Theme" })).toBeVisible();
  });

  test("source filter dropdown shows options from stats", async ({ page }) => {
    const sourceSelect = page.locator("select").first();
    await expect(sourceSelect).toContainText("All Sources");
  });

  test("business relevance filter label and dropdown appear on relevant tab", async ({ page }) => {
    // Use the label element specifically
    await expect(page.locator("label").filter({ hasText: "Business Relevance" })).toBeVisible();
    await expect(page.locator("select").filter({ hasText: "All Relevant" })).toBeVisible();
  });

  test("business relevance filter dropdown has correct options", async ({ page }) => {
    const relevanceSelect = page.locator("select").filter({ hasText: "All Relevant" });
    await expect(relevanceSelect).toContainText("All Relevant (High+Medium)");
    await expect(relevanceSelect).toContainText("High Business Relevance");
    await expect(relevanceSelect).toContainText("Medium Business Relevance");
  });

  test("confidence threshold slider is visible", async ({ page }) => {
    await expect(page.getByText(/Confidence:/)).toBeVisible();
    const slider = page.locator('input[type="range"]');
    await expect(slider).toBeVisible();
  });

  // ─── Pagination ───

  test("pagination is not shown when data fits one page", async ({ page }) => {
    // With only 3 mock grants and pageSize=20, there should be no pagination
    const pageText = page.getByText(/Page \d+ of \d+/);
    await expect(pageText).not.toBeVisible();
  });

  // ─── Empty State ───

  test("shows empty state when no grants match filters", async ({ page }) => {
    // Override the grants route to return empty
    await page.route("**/api/grants?**", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "X-Total-Count": "0", "Content-Type": "application/json" },
        body: JSON.stringify([]),
      });
    });
    // Reload to trigger new mock
    await page.reload();
    await page.waitForSelector("text=Grant Explorer");
    await expect(page.getByText("No grants found")).toBeVisible();
  });
});
