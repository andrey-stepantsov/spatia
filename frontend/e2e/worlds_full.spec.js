import { test, expect } from '@playwright/test';

test.describe('Worlds UI Walkthrough', () => {

    // Use a unique suffix
    const timestamp = Date.now();
    const alphaName = `alpha-${timestamp}`;
    const betaName = `beta-${timestamp}`;

    test.beforeEach(async ({ page }) => {
        // Go to home
        await page.goto('/');
    });

    test('Full Lifecycle: Create -> Snapshot -> Clone -> Eject', async ({ page }) => {
        test.setTimeout(60000);

        // --- 1. OPEN MENU ---
        const worldButton = page.locator('button:has-text("World")').first();
        await expect(worldButton).toBeVisible();
        await worldButton.click();

        // --- 2. CREATE NEW WORLD ---
        await page.getByText('+ Create New World').click();
        await expect(page.getByText('Create New World', { exact: true })).toBeVisible();
        await page.getByPlaceholder('my-new-world').fill(alphaName);
        await page.getByRole('button', { name: 'Create World' }).click();
        await expect(worldButton).toContainText(alphaName);

        // --- 3. SNAPSHOT ---
        await worldButton.click();

        const alphaRow = page.locator('.group', { hasText: alphaName });
        const meatball = alphaRow.locator('button:has-text("⋮")');
        await expect(meatball).toBeVisible();
        await meatball.click();

        // Context menu appears
        const snapshotBtn = page.locator('button', { hasText: 'Snapshot' });
        await expect(snapshotBtn).toBeVisible();

        const snapshotDialogPromise = page.waitForEvent('dialog', { timeout: 10000 });
        await snapshotBtn.evaluate(b => b.click());
        const snapshotDialog = await snapshotDialogPromise;
        expect(snapshotDialog.message()).toContain('Snapshot created');
        await snapshotDialog.accept();


        // --- 4. CLONE ---
        // Ensure UI is interactive
        await page.waitForTimeout(500);

        // Menu might still be open from previous step. Check before clicking.
        const worldsHeader = page.getByText('Available Worlds');
        if (!await worldsHeader.isVisible()) {
            await worldButton.click();
        }
        await expect(worldsHeader).toBeVisible();

        await meatball.click();

        const cloneBtn = page.getByText('Clone');
        await expect(cloneBtn).toBeVisible();

        // We need to handle two dialogs: The Prompt (Input) and the Success Alert
        let promptResolved = false;
        let alertResolved = false;

        const dialogHandler = async (dialog) => {
            if (dialog.type() === 'prompt') {
                await dialog.accept(betaName);
                promptResolved = true;
            } else if (dialog.type() === 'alert') {
                if (dialog.message().includes('Cloned')) {
                    alertResolved = true;
                }
                await dialog.accept();
            } else {
                await dialog.dismiss();
            }
        };

        page.on('dialog', dialogHandler);

        await cloneBtn.evaluate(b => b.click());

        await expect.poll(() => promptResolved && alertResolved).toBeTruthy();
        page.removeListener('dialog', dialogHandler);


        // --- 5. EJECT ---
        if (!await worldsHeader.isVisible()) {
            await worldButton.click();
        }
        await expect(worldsHeader).toBeVisible();

        // Find beta row
        const betaRow = page.locator('.group', { hasText: betaName });
        await expect(betaRow).toBeVisible();

        const betaMeatball = betaRow.locator('button:has-text("⋮")');
        await betaMeatball.click();

        await page.getByText('Eject').evaluate(b => b.click());
        await expect(page.getByText('Critical Action: Ejecting World')).toBeVisible();

        await page.getByPlaceholder(betaName).fill(betaName);
        await page.getByRole('button', { name: 'Final Eject' }).click();

        await worldButton.click();
        await expect(page.locator('.group', { hasText: betaName })).not.toBeVisible();

    });

});
