import { test, expect } from '@playwright/test';

test.describe('Visual Threads & Conflict Fold', () => {
    test('should render threads (edges) between atoms', async ({ page }) => {
        // 1. Mock API to return known atoms and threads
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'atomA', content: 'Atom A', x: 0, y: 0, status: 1 },
                    { id: 'atomB', content: 'Atom B', x: 300, y: 0, status: 1 }
                ]
            });
        });

        await page.route('/api/threads', async route => {
            await route.fulfill({
                json: [
                    { source: 'atomA', target: 'atomB' }
                ]
            });
        });

        // Mock SSE
        await page.route('/api/events', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: 'event: connected\ndata: {}\n\n'
            });
        });

        // 2. Go to page
        await page.goto('/');

        // 3. Verify nodes exist
        await expect(page.getByText('Atom A')).toBeVisible();
        await expect(page.getByText('Atom B')).toBeVisible();

        // 4. Verify edge exists (React Flow edges usually have a specific class or SVG element)
        // We look for the edge by its ID we constructed: e{source}-{target}
        // But React Flow renders them deep in SVG. We can check for the edge path.
        // Or closer: check if .react-flow__edge exists
        await expect(page.locator('.react-flow__edge')).toBeVisible();
    });

    test('should show warning glow on collision', async ({ page }) => {
        // Mock data with two atoms ALREADY overlapping (position-based test)
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    // Two atoms with overlapping positions
                    { id: 'col1', content: 'Collider 1', x: 100, y: 150, status: 1 },
                    { id: 'col2', content: 'Collider 2', x: 120, y: 160, status: 1 } // Overlapping!
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

        const node1 = page.getByText('Collider 1');
        const node2 = page.getByText('Collider 2');

        await expect(node1).toBeVisible();
        await expect(node2).toBeVisible();

        // Verify Conflict Detection (runs every 500ms)
        // Both atoms are overlapping, so collision should be detected
        await page.waitForSelector('.conflict-fold', { timeout: 2000 });

        // Both nodes should have conflict-fold class
        await expect(page.locator('.conflict-fold')).toHaveCount(2);
        await expect(page.locator('.conflict-fold').first()).toBeVisible();
    });
});
