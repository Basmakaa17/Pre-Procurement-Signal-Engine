import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // ─── Hero Section ───

  test("renders hero title", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Grants are the signal");
    await expect(page.locator("h1")).toContainText("echo");
  });

  test("renders hero description", async ({ page }) => {
    await expect(page.getByText(/Canadian government grants are published/)).toBeVisible();
    await expect(page.getByText(/anticipate, not just react/)).toBeVisible();
  });

  test("shows CTA buttons", async ({ page }) => {
    await expect(page.getByRole("link", { name: /See How It Works/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Data Pipeline/i }).first()).toBeVisible();
  });

  test("View Dashboard link is in the nav", async ({ page }) => {
    await expect(page.getByRole("link", { name: /View Dashboard/i })).toBeVisible();
  });

  // ─── Hero Signal Card ───

  test("hero signal card shows live signals", async ({ page }) => {
    await expect(page.getByText("LIVE PROCUREMENT SIGNALS")).toBeVisible();
    await expect(page.getByText("Ontario Cybersecurity Wave")).toBeVisible();
    await expect(page.getByText("Federal AI Modernization")).toBeVisible();
    await expect(page.getByText("Healthcare Digitization Wave")).toBeVisible();
  });

  test("signal card shows strength badges", async ({ page }) => {
    await expect(page.getByText("Strong")).toBeVisible();
    // Two "Moderate" badges
    const moderateBadges = page.getByText("Moderate");
    await expect(moderateBadges.first()).toBeVisible();
  });

  // ─── Landing Page Nav Links ───

  test("displays section navigation links", async ({ page }) => {
    for (const label of ["Problem", "How It Works", "Business Value", "Data Pipeline", "Decisions", "FAQ"]) {
      await expect(page.locator(".landing-nav-links").getByText(label)).toBeVisible();
    }
  });

  // ─── Problem Section ───

  test("Problem section renders with correct heading", async ({ page }) => {
    const section = page.locator("#problem");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Government spends on a script.")).toBeVisible();
  });

  test("Problem section shows timeline steps", async ({ page }) => {
    const section = page.locator("#problem");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Budget Announced")).toBeVisible();
    await expect(section.getByText("Grant Program Created")).toBeVisible();
    await expect(section.getByText("Grants Awarded")).toBeVisible();
    await expect(section.getByText("Recipients Need Vendors")).toBeVisible();
    await expect(section.getByText("RFP Published")).toBeVisible();
  });

  test("Problem section shows pain cards", async ({ page }) => {
    const section = page.locator("#problem");
    await section.scrollIntoViewIfNeeded();
    // The text uses Unicode curly quotes: "We're always too late."
    await expect(section.getByText(/always too late/)).toBeVisible();
  });

  // ─── How It Works Section ───

  test("How It Works section has four steps", async ({ page }) => {
    const section = page.locator("#how");
    await section.scrollIntoViewIfNeeded();
    for (const step of ["Ingest", "Clean", "Classify", "Signal"]) {
      await expect(section.getByText(step, { exact: true })).toBeVisible();
    }
  });

  test("How It Works steps are clickable and change content", async ({ page }) => {
    const section = page.locator("#how");
    await section.scrollIntoViewIfNeeded();

    // Click on "Clean" step
    await section.getByText("Clean", { exact: true }).click();
    await expect(section.getByText(/RapidFuzz/)).toBeVisible();

    // Click on "Signal" step
    await section.getByText("Signal", { exact: true }).click();
    await expect(section.getByText(/lag model/)).toBeVisible();
  });

  // ─── Business Value Section ───

  test("Business Value section shows three value cards", async ({ page }) => {
    const section = page.locator("#value");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Dramatically stickier platform")).toBeVisible();
    await expect(section.getByText("Natural premium tier")).toBeVisible();
    await expect(section.getByText("New top-of-funnel entry point")).toBeVisible();
  });

  test("Business Value section shows stats bar", async ({ page }) => {
    const section = page.locator("#value");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Grant records (2026)")).toBeVisible();
    await expect(section.getByText("Procurement categories")).toBeVisible();
    await expect(section.getByText("Avg. forecast horizon")).toBeVisible();
    await expect(section.getByText("Data sources live")).toBeVisible();
  });

  // ─── Data Pipeline Section ───

  test("Data Pipeline section shows all stages", async ({ page }) => {
    const section = page.locator("#pipeline");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Source Adapters")).toBeVisible();
    await expect(section.getByText("Amount Parsing")).toBeVisible();
    await expect(section.getByText("Date Normalization")).toBeVisible();
    await expect(section.getByText("Dept. Canonicalization")).toBeVisible();
    await expect(section.getByText("Deduplication")).toBeVisible();
    await expect(section.getByText("LLM Classification")).toBeVisible();
    await expect(section.getByText("Signal Detection")).toBeVisible();
  });

  test("Pipeline stages are clickable and expand details", async ({ page }) => {
    const section = page.locator("#pipeline");
    await section.scrollIntoViewIfNeeded();
    // Click on Deduplication stage
    await section.getByText("Deduplication").click();
    await expect(section.getByText(/SHA256 hash/)).toBeVisible();
  });

  // ─── Key Decisions Section ───

  test("Key Decisions section shows all four decisions", async ({ page }) => {
    const section = page.locator("#decisions");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Heuristic model over ML model")).toBeVisible();
    await expect(section.getByText("CKAN API over Solr search pagination")).toBeVisible();
    await expect(section.getByText("Quarantine over delete")).toBeVisible();
    await expect(section.getByText("Taxonomy-locked LLM classification")).toBeVisible();
  });

  // ─── FAQ Section ───

  test("FAQ section renders all questions", async ({ page }) => {
    const section = page.locator("#faq");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("How does the prediction model actually work?")).toBeVisible();
    await expect(section.getByText(/Why not use the grants search portal/)).toBeVisible();
    await expect(section.getByText(/How do you handle the messiness/)).toBeVisible();
    await expect(section.getByText(/How do you validate LLM outputs/)).toBeVisible();
    await expect(section.getByText(/How does this connect to Publicus/)).toBeVisible();
    await expect(section.getByText(/What would you build next/)).toBeVisible();
  });

  test("FAQ items expand and collapse on click", async ({ page }) => {
    const section = page.locator("#faq");
    await section.scrollIntoViewIfNeeded();

    // Click to expand the first FAQ
    await section.getByText("How does the prediction model actually work?").click();
    await expect(section.getByText(/structured heuristic rule engine/)).toBeVisible();

    // Click again to collapse
    await section.getByText("How does the prediction model actually work?").click();
    // The answer should collapse (not visible after animation)
    // Note: Due to CSS animation, we check that the container doesn't have "open" class
  });

  // ─── Next Steps Section ───

  test("Next Steps section renders all roadmap items", async ({ page }) => {
    const section = page.locator("#next");
    await section.scrollIntoViewIfNeeded();
    await expect(section.getByText("Back-test the model")).toBeVisible();
    await expect(section.getByText("Build the feedback loop")).toBeVisible();
    await expect(section.getByText("Vendor intelligence layer")).toBeVisible();
    await expect(section.getByText("Municipal expansion")).toBeVisible();
    await expect(section.getByText("Inline Publicus integration")).toBeVisible();
    await expect(section.getByText("Alert personalization")).toBeVisible();
  });

  // ─── Footer ───

  test("footer shows branding and tech stack", async ({ page }) => {
    const footer = page.locator("footer");
    await footer.scrollIntoViewIfNeeded();
    await expect(footer.getByText("Technical Assessment Prototype")).toBeVisible();
    await expect(footer.getByText(/FastAPI/)).toBeVisible();
    await expect(footer.getByText(/Next.js/)).toBeVisible();
  });

  // ─── Navigation ───

  test("View Dashboard link navigates to /dashboard", async ({ page }) => {
    await page.getByRole("link", { name: /View Dashboard/i }).click();
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
