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
        // 1. Mock data with two atoms far apart
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'col1', content: 'Collider 1', x: 0, y: 0, status: 1 },
                    { id: 'col2', content: 'Collider 2', x: 0, y: 400, status: 1 } // Far below
                ]
            });
        });

        await page.route('/api/threads', async route => {
            await route.fulfill({ json: [] });
        });

        await page.goto('/');

        const node1 = page.getByText('Collider 1');
        const node2 = page.getByText('Collider 2');

        await expect(node1).toBeVisible();
        await expect(node2).toBeVisible();

        // 2. Drag Node 2 onto Node 1
        // We need to drag the handle or the node body. SpatiaNode body is draggable.
        const box1 = await node1.boundingBox();
        const box2 = await node2.boundingBox();

        if (box1 && box2) {
            await page.mouse.move(box2.x + box2.width / 2, box2.y + box2.height / 2);
            await page.mouse.down();
            // Move to overlap with Node 1
            await page.mouse.move(box1.x + box1.width / 2, box1.y + box1.height / 2, { steps: 10 });
            await page.mouse.up();
        }

        // 3. Verify Warning Glow (Conflict Fold)
        // The code adds 'conflict-fold' class and inline styles.
        // We check for the class.
        await expect(page.locator('.conflict-fold')).toHaveCount(2); // Both should glow
    });
});
