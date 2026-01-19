import { test, expect } from '@playwright/test';
import { waitForConnection } from './helpers/waitForConnection';

test.describe('Spatial Envelopes', () => {
    test.beforeEach(async ({ page }) => {
        // Keep data mocks, but allow real connection (health/SSE) to avoid reconnect loops
        await page.route('/api/threads', async route => route.fulfill({ json: [] }));
        await page.route('/api/atoms', async route => route.fulfill({ json: [] })); // Default empty atoms
        // Removed /api/events and /api/health mocks to use real backend connection


        page.on('console', msg => console.log(`BROWSER: ${msg.text()}`));
        page.on('pageerror', err => console.log(`BROWSER ERROR: ${err}`));
    });

    test('should detect domain conflict when atom inside envelope', async ({ page }) => {
        test.setTimeout(60000); // Increase timeout for slow env

        // 1. Mock Data: One "System" envelope, One "Generic" atom ALREADY INSIDE envelope
        await page.route('/api/envelopes', async route => {
            await route.fulfill({
                json: [
                    { id: 'env-sys', domain: 'system', x: 100, y: 100, w: 400, h: 400 }
                ]
            });
        });

        // Atom positioned at center of envelope (300, 300)
        // This creates domain mismatch: generic atom inside system envelope
        await page.route('/api/atoms', async route => {
            await route.fulfill({
                json: [
                    { id: 'atom-gen', content: 'Intruder', domain: 'generic', x: 250, y: 250, status: 1 }
                ]
            });
        });

        // Mock Geometry Sync
        await page.route('/api/geometry', async route => route.fulfill({ json: { status: 'ok' } }));

        // 2. Load Page
        await page.goto('/');
        await waitForConnection(page);

        // 3. Verify Elements Load
        const atom = page.getByText('Intruder');
        await expect(atom).toBeVisible();
        await expect(page.getByText('system')).toBeVisible();

        // 4. Verify Conflict Detection (runs every 500ms)
        // Atom center (250+125, 250+75) = (375, 325) is inside envelope (100,100,400,400)
        // Domain mismatch: generic !== system -> conflict
        await page.waitForSelector('.conflict-fold', { timeout: 2000 });

        // Should have exactly 1 conflict (the atom)
        await expect(page.locator('.conflict-fold')).toHaveCount(1);
        await expect(page.locator('.conflict-fold')).toBeVisible();

        // The atom should have the conflict-fold class
        const nodeWithConflict = page.locator('.react-flow__node.conflict-fold');
        await expect(nodeWithConflict).toBeVisible();
        await expect(nodeWithConflict).toContainText('Intruder');
    });

    test('should allow creating new envelope', async ({ page }) => {
        // Mock API
        await page.route('/api/envelopes', async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({ json: [] });
            } else if (route.request().method() === 'POST') {
                await route.fulfill({ status: 200, json: { status: 'created' } });
            }
        });
        await page.route('/api/atoms', async route => route.fulfill({ json: [] }));


        await page.goto('/');

        // Click Button
        await page.getByRole('button', { name: '+ BOUNDARY' }).click();

        // Fill Modal
        await expect(page.locator('text=Create Boundary')).toBeVisible();
        await page.fill('input[placeholder="env-..."]', 'env-new');
        await page.locator('button:has-text("Create")').click();

        // Ideally we verify the POST request happened
        // Or if we reload, it appears. But here we just mock the POST.
        // We can verify request
        const request = await page.waitForRequest(req => req.url().includes('/api/envelopes') && req.method() === 'POST');
        expect(request).toBeTruthy();
    });
});
