import { test, expect } from '@playwright/test';

test.describe('Shatter & Persistence', () => {
    test.beforeEach(async ({ page }) => {
        // Default mocks to avoid errors on load
        await page.route('/api/atoms', async route => route.fulfill({ json: [] }));
        await page.route('/api/threads', async route => route.fulfill({ json: [] }));
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
        // The app calls fetchAtoms() after shatter success.
        // We can update the /api/atoms mock *after* the initial load, 
        // but since we are inside a test step, we can override the route now? 
        // Actually, Playwright routes are LIFO (last registered match wins), 
        // so we register a new route for the *next* request.
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [{ id: 'atoms/new_idea.md', content: '# My Idea', x: 0, y: 0, status: 1 }]
            });
        });

        // 4. Interact with Shatter Portal
        await page.getByPlaceholder('Path (e.g. atoms/idea.md)').fill('atoms/new_idea.md');
        await page.getByPlaceholder('Content (optional)').fill('# My Idea');
        await page.getByRole('button', { name: 'SHATTER ATOM' }).click();

        // 5. Verify API was called
        // We can wait a bit or just rely on the UI update which implies success
        // But the check inside the route handler ensures content correctness.

        // 6. Verify UI Updated
        // The new mock for /api/atoms should be hit.
        await expect(page.getByText('atoms/new_idea.md')).toBeVisible();

        expect(shatterCalled).toBe(true);
    });

    test('should persist geometry on drag stop', async ({ page }) => {
        // 1. Initial State: One atom
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [{ id: 'draggable_atom', content: 'Drag Me', x: 100, y: 100, status: 1 }]
            });
        });
        await page.goto('/');

        // 2. Mock Geometry API
        let geometryPayload = null;
        await page.route('/api/geometry', async route => {
            geometryPayload = route.request().postDataJSON();
            await route.fulfill({ json: { status: 'ok' } });
        });

        // 3. Perform Drag
        const node = page.getByText('Drag Me');
        await expect(node).toBeVisible();
        const box = await node.boundingBox();

        if (box) {
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.down();
            // Move 100px right, 50px down
            await page.mouse.move(box.x + box.width / 2 + 100, box.y + box.height / 2 + 50, { steps: 10 });
            await page.mouse.up();
        }

        // 4. Verify Persistence Call
        // Wait for the request to happen (it's async in dragStop)
        await page.waitForTimeout(500);

        expect(geometryPayload).not.toBeNull();
        expect(geometryPayload.length).toBe(1);
        expect(geometryPayload[0].atom_id).toBe('draggable_atom');
        // We moved +100 x, +50 y. Logic in ReactFlow is robust, but coordinate calculation 
        // depends on zoom/pan level. Assuming default zoom 1 and no pan:
        // Initial 100, 100. New should be roughly 200, 150.
        // We'll just check "roughly" or that it changed significantly.
        expect(geometryPayload[0].x).toBeGreaterThan(140);
        expect(geometryPayload[0].y).toBeGreaterThan(120);
    });
});
