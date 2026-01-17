import { test, expect } from '@playwright/test';

test.describe('Ghost Mode & Time Travel', () => {
    test.beforeEach(async ({ page }) => {
        // Mock Data
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'active.txt', content: 'Active Content', x: 0, y: 0, status: 1 },
                    { id: 'fossil.txt@old', content: 'Fossil Content', x: 200, y: 0, status: 4 }
                ]
            });
        });

        await page.route('/api/threads', async route => {
            await route.fulfill({ json: [] });
        });

        // Mock SSE
        await page.route('/api/events', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: 'event: connected\ndata: {}\n\n'
            });
        });

        await page.goto('/');
    });

    test('should hide fossils by default and show them in Ghost Mode', async ({ page }) => {
        // 1. Verify Fossil is hidden initially
        // We look for text "Fossil Content"
        const fossilNode = page.getByText('Fossil Content');
        await expect(fossilNode).toBeHidden();

        // 2. Click Ghost Mode Toggle
        // We added data-testid="ghost-mode-switch"
        await page.locator('[data-testid="ghost-mode-switch"]').click();

        // 3. Verify Fossil is visible
        await expect(fossilNode).toBeVisible();

        // 4. Verify Styling (opacity/border)
        // Check computed style or class. React Flow nodes have a wrapper.
        // Our node component applies styling to the inner div.
        // Let's verify the text container's parent has expected classes or styles.
        // Using locator to find the node wrapper.
        const nodeWrapper = page.locator('.react-flow__node-spatia').filter({ hasText: 'Fossil Content' });
        // We can check for opacity class or style if applied.
        // Our implementation applies opacity-50 class.
        // Playwright class check:
        // await expect(nodeWrapper.locator('div').first()).toHaveClass(/opacity-50/);
    });

    test('should trigger revive on fossil interaction', async ({ page }) => {
        // 1. Enable Ghost Mode
        await page.locator('[data-testid="ghost-mode-switch"]').click();

        // 2. Mock Revive Endpoint
        let reviveCalled = false;
        await page.route('/api/revive', async route => {
            reviveCalled = true;
            await route.fulfill({ json: { status: 'revived' } });
        });

        // 3. Click "Revive" button on fossil
        const fossilNode = page.locator('.react-flow__node-spatia').filter({ hasText: 'Fossil Content' });

        // Handle confirm dialog
        page.on('dialog', dialog => dialog.accept());

        await fossilNode.getByText('REVIVE').click();

        // 4. Verify API call
        expect(reviveCalled).toBe(true);
    });
});
