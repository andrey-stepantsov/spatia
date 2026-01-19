import { test, expect } from '@playwright/test';
import { waitForConnection, waitForCanvas } from './helpers/waitForConnection';

test('Summoning Flow: Hollow Construct -> Portals -> Summon', async ({ page }) => {
    // 1. App Load
    test.setTimeout(60000); // Increase timeout
    await page.goto('/');
    await waitForConnection(page);
    await waitForCanvas(page);

    // 2. Clear existing (Optional, or assume clean DB/unique ID)
    // We'll use a unique ID for the test run
    const testId = `hollow_test_${Date.now()}`;

    // 3. Create "Hollow" Construct
    // a. Toggle Hollow
    // Using text matching or class matching. 
    // The toggle is in the Shatter Portal.
    await page.getByTestId('hollow-switch').click();

    // b. Enter Path (ID)
    await page.fill('input[placeholder*="Path"]', testId);

    // c. Click Shatter (Create)
    await page.click('button:has-text("SHATTER ATOM")');

    // 4. Verify Blue Node Appears
    // Wait for node to appear
    const nodeSelector = `.react-flow__node-spatia:has-text("${testId}")`;
    await page.waitForSelector(nodeSelector);
    const node = page.locator(nodeSelector);

    // Check Blue Glow (Shadow status) - Target inner div
    // The wrapper has standard classes. The Inner component has the border-blue-500
    await expect(node.locator('div').first()).toHaveClass(/border-blue-500/);

    // 5. Add Portal Link
    // a. Expand Portals
    await node.getByTestId('portals-toggle').click();

    // b. Fill Portal Path
    await node.getByTestId('portal-input').fill('/etc/hosts');

    // c. Submit Portal
    await node.getByTestId('add-portal-btn').click();

    // d. Verify Portal in List
    await expect(node.getByText('/etc/hosts')).toBeVisible();

    // 6. Summon
    // a. Click Summon
    await node.getByTestId('summon-btn').click();

    // b. Confirm Modal
    await expect(page.locator('text=Summon Intelligence')).toBeVisible();
    await page.locator('.fixed').filter({ hasText: 'Summon Intelligence' }).getByRole('button', { name: 'Summon' }).click();

    // 7. Verify Transition
    // Should lose Blue status and gain Yellow (Claim) or Purple (Witness)
    // Wait for it to NOT be blue.
    // Wait for it to NOT be blue (allow time for backend/AI to process)
    await expect(node.locator('div').first()).not.toHaveClass(/border-blue-500/, { timeout: 45000 });
    // Should eventually have Witnessing (Purple) or Endorsed (Green) if fast
    // Let's assert it is one of the non-hollow states.
    // Or check for "Witnessing" if we can catch it.
});
