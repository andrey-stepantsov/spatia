
import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

test.describe('Realtime Updates', () => {
    test.beforeEach(async () => {
        // Reset environment before test to ensure clean state
        try {
            // Force devbox usage to ensure correct python/uvicorn are found
            execSync('devbox run python3 scripts/reset_env.py', { cwd: '..' });
        } catch (e) {
            console.log('Reset env failed or script not found, ignoring for now');
        }
    });

    test('should update node status in real-time', async ({ page }) => {
        // 1. Shatter a new atom (Hollow)
        await page.goto('/');

        // Fill the Shatter Portal
        await page.getByPlaceholder('Path (e.g. atoms/idea.md)').fill('atoms/e2e_realtime.md');
        await page.getByPlaceholder('Content (optional)').fill(';; intent\n(defun test ())');

        // Toggle Hollow switch
        await page.getByTestId('hollow-switch').click();

        // Click Shatter
        await page.getByRole('button', { name: 'SHATTER ATOM' }).click();

        // Verify Node appears (Blue Border for Shadow/Status 0)
        // Verify Node appears (Blue Border for Shadow/Status 0)
        // Locator strategy: Find the main container (rounded-xl) that contains the specific atom text
        const nodeContainer = page.locator('div.rounded-xl').filter({ hasText: 'atoms/e2e_realtime.md' }).first();
        await expect(nodeContainer).toBeVisible({ timeout: 10000 });
        await expect(nodeContainer).toHaveClass(/border-blue-500/);

        // 2. Summon the Atom
        const summonBtn = nodeContainer.getByTestId('summon-btn');
        await expect(summonBtn).toBeVisible();
        await summonBtn.click();

        // Confirm Modal
        // Use dialog selector to be precise
        await page.getByRole('dialog').getByRole('button', { name: 'Summon' }).click();

        // 3. Verify Status Change

        // await expect(node).not.toHaveClass(/border-blue-500/, { timeout: 10000 });

        // Check for "Witnessed" (Purple) or "Claim" (Yellow)
        await expect(nodeContainer).toHaveClass(/border-(purple|yellow)-500/, { timeout: 10000 });
    });
});
