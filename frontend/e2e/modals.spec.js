// @ts-check
import { test, expect } from '@playwright/test';
import { waitForConnection } from './helpers/waitForConnection';

test.describe('Modal Interactions', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173');
        // Wait for connection to establish
        await waitForConnection(page);
    });

    test('should create and delete a spatial envelope', async ({ page }) => {
        // Forward console logs
        page.on('console', msg => console.log(`BROWSER: ${msg.text()}`));

        // 1. Open Create Modal
        await page.locator('button:has-text("+ BOUNDARY")').click();
        await expect(page.locator('text=Create Boundary')).toBeVisible();

        // 2. Fill Form - use unique domain to avoid strict mode violations
        const timestamp = Date.now();
        const envelopeId = `env-test-${timestamp}`;
        const envelopeDomain = `test-domain-${timestamp}`;
        await page.fill('input[placeholder="env-..."]', envelopeId);
        await page.fill('input[placeholder="generic"]', envelopeDomain);
        await page.locator('button:has-text("Create")').click();

        // 3. Verify Creation - Envelope displays domain label, not ID
        await expect(page.getByText(envelopeDomain)).toBeVisible();

        // 4. Select Envelope - click on React Flow node to trigger selection
        // Clicking just the text doesn't trigger React Flow's selection state
        // 4. Select Envelope - click on React Flow node to trigger selection
        const envelopeNode = page.locator(`[data-testid="rf__node-${envelopeId}"]`);
        await envelopeNode.waitFor({ state: 'visible', timeout: 5000 });

        // Retry selection if delete button doesn't appear
        for (let i = 0; i < 3; i++) {
            console.log(`Selection attempt ${i + 1}...`);
            // Click the inner content div which has the click listener, avoiding the Resizer potentially
            await envelopeNode.locator('.relative.group').click({ force: true });

            try {
                // Wait for button to be attached to DOM first
                await page.locator('button:has-text("DELETE")').waitFor({ state: 'attached', timeout: 2000 });
                break;
            } catch (e) {
                if (i === 2) throw e;
            }
        }

        // 5. Wait for DELETE button to appear (shows on selection)
        const deleteBtn = page.locator('button:has-text("DELETE")');
        await expect(deleteBtn).toBeVisible({ timeout: 5000 });
        // Small stability wait
        await page.waitForTimeout(500);
        await deleteBtn.click({ force: true });

        // 6. Verify Confirmation Modal appears
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });
        await expect(page.getByRole('heading', { name: 'Delete Boundary' })).toBeVisible();

        // 7. Confirm deletion by clicking Delete button in modal
        // Use more specific selector to avoid conflict with the node's DELETE button
        await dialog.getByRole('button', { name: 'Delete' }).click({ force: true });

        // 9. Verify Removal - domain label should disappear
        await expect(page.getByText(envelopeDomain)).not.toBeVisible();
    });

    test('should trigger summon modal', async ({ page }) => {
        // Find a shadow atom (Blue, status 0) to summon
        // We might need to create one first if none exist, but for now assuming one exists or we create one via shatter

        // Let's create a temporary atom to test this reliably
        const testPath = `atoms/test-summon-${Date.now()}.md`;
        await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', testPath);
        await page.fill('textarea[placeholder="Content (optional)"]', 'Checking summon modal');
        await page.locator('button:has-text("SHATTER ATOM")').click();

        // Wait for atom to appear
        await expect(page.locator(`text=${testPath}`)).toBeVisible();
        const atomNode = page.locator(`text=${testPath}`).locator('xpath=../../..'); // Navigate up to container

        // Click Summon
        await atomNode.locator('button:has-text("Summon")').click();

        // Verify Modal
        await expect(page.locator('text=Summon Intelligence')).toBeVisible();
        await expect(page.locator('text=gemini-2.5-flash')).toBeVisible(); // Default model

        // Cancel
        await page.locator('button:has-text("Cancel")').click();
        await expect(page.locator('text=Summon Intelligence')).not.toBeVisible();
    });
});
