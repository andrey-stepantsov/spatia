import { test, expect } from '@playwright/test';

test.describe('Shatter & Persistence', () => {

    test.describe('Mocked UI Tests', () => {
        test.beforeEach(async ({ page }) => {
            // Default mocks to avoid errors on load
            await page.route('/api/atoms', async route => route.fulfill({ json: [] }));
            await page.route('/api/threads', async route => route.fulfill({ json: [] }));
            // Mock SSE
            await page.route('/api/events', async route => {
                await route.fulfill({
                    status: 200,
                    contentType: 'text/event-stream',
                    body: 'event: connected\ndata: {}\n\n'
                });
            });
        });

        test('should shatter a new atom and display it', async ({ page }) => {
            // 1. Setup initial state (empty)
            await page.goto('/');

            // 2. Mock the Shatter API call
            let shatterCalled = false;
            await page.route('/api/shatter', async route => {
                const data = route.request().postDataJSON();
                expect(data.path).toBe('atoms/new_idea.md');
                expect(data.content).toBe('# My Idea');
                shatterCalled = true;
                await route.fulfill({ json: { atom_id: 'atoms/new_idea.md' } });
            });

            // 3. Mock the subsequent fetchAtoms call to return the new atom
            await page.route('/api/atoms', async route => {
                await route.fulfill({
                    json: [{ id: 'atoms/new_idea.md', content: '# My Idea', x: 0, y: 0, status: 1 }]
                });
            });

            // 4. Interact with Shatter Portal
            await page.getByPlaceholder('Path (e.g. atoms/idea.md)').fill('atoms/new_idea.md');
            await page.getByPlaceholder('Content (optional)').fill('# My Idea');
            await page.getByRole('button', { name: 'SHATTER ATOM' }).click();

            // 6. Verify UI Updated
            await expect(page.getByText('atoms/new_idea.md')).toBeVisible();

            expect(shatterCalled).toBe(true);
        });
    });

    test.describe('Integration Tests (Real API)', () => {
        test('should persist geometry via API', async ({ page, request }) => {
            // 1. Create atom via UI
            await page.goto('/');

            // Wait for connection to establish
            // Wait for connection to establish (CONNECTING... should disappear)
            await page.locator('text=CONNECTING...').waitFor({ state: 'hidden', timeout: 10000 });

            const testPath = `atoms/persist-test-${Date.now()}.md`;
            await page.fill('input[placeholder="Path (e.g. atoms/idea.md)"]', testPath);
            await page.fill('textarea[placeholder="Content (optional)"]', 'Geometry persistence test');
            await page.click('button:has-text("SHATTER ATOM")');

            // Wait for atom to appear on canvas
            await page.waitForTimeout(1000);
            const node = page.locator(`div.react-flow__node-spatia:has-text("${testPath}")`);
            await expect(node).toBeVisible({ timeout: 20000 });

            // 2. Update geometry directly via API
            // Note: In real app, API is at same origin. In test, request fixture handles it.
            // But if we use 'request' fixture, we might need baseURL.
            // Let's assume baseURL is set in playwright.config.
            const geometryUpdate = await request.post('/api/geometry', {
                data: [{ atom_id: testPath, x: 500, y: 300 }]
            });
            expect(geometryUpdate.ok()).toBe(true);

            // 3. Reload page and verify position persisted
            await page.reload();

            // Wait for atoms to load
            // Wait for atoms to load
            await page.locator('text=CONNECTING...').waitFor({ state: 'hidden', timeout: 10000 });

            // 4. Verify geometry was persisted by checking node position after reload
            const persistedNode = page.locator(`div.react-flow__node-spatia:has-text("${testPath}")`);
            await expect(persistedNode).toBeVisible({ timeout: 10000 });

            // Get position - React Flow nodes have transform style
            const transform = await persistedNode.evaluate(el => {
                const style = window.getComputedStyle(el);
                return style.transform;
            });

            // React Flow uses transform: translate(500px, 300px)
            // It might be matrix(...) but typically expect 500/300 nums.
            expect(transform).toMatch(/matrix.*500.*300.*|translate.*500px.*300px/);
        });
    });
});
