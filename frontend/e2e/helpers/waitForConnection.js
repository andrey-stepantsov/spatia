import { expect } from '@playwright/test';

/**
 * Wait for the Spatia app connection to be established.
 * 
 * This helper waits for the "CONNECTING..." label to disappear,
 * indicating that the SSE connection is ready and the app is
 * fully initialized.
 * 
 * @param {Page} page - Playwright page object
 * @param {number} timeout - Maximum time to wait in milliseconds (default: 30000)
 */
export async function waitForConnection(page, timeout = 30000) {
    await expect(page.locator('text=CONNECTING...')).not.toBeVisible({ timeout });
    // Extra buffer to ensure SSE is fully established
    await page.waitForTimeout(500);
}

/**
 * Wait for the React Flow canvas to be ready.
 * 
 * @param {Page} page - Playwright page object
 */
export async function waitForCanvas(page) {
    await expect(page.locator('.react-flow__renderer')).toBeVisible();
}
