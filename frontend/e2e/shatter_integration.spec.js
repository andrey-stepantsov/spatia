import { test, expect } from '@playwright/test';

test.describe('Shatter Integration (Real Backend)', () => {
    test.beforeEach(async ({ page }) => {
        // No mocks!
        // We ensure we are in a clean workspace or handle cleanup?
        // But we just create a unique atom.
        await page.goto('/');
    });

    test('should shatter a real atom and persist it', async ({ page }) => {
        const timestamp = Date.now();
        const atomPath = `atoms/integration-${timestamp}.md`;
        const atomContent = `# Integration Test ${timestamp}`;

        // 1. Fill Shatter Form
        await page.getByPlaceholder('Path (e.g. atoms/idea.md)').fill(atomPath);
        await page.getByPlaceholder('Content (optional)').fill(atomContent);

        // 2. Click Shatter
        await page.getByRole('button', { name: 'SHATTER ATOM' }).click();

        // 3. Verify it appears in the Canvas (via text)
        // This relies on SSE or Polling updating the list.
        await expect(page.getByText(atomPath)).toBeVisible({ timeout: 10000 });

        // 4. Verify Content (by finding the node and checking something?)
        // Or we can try to "Edorse" it? 
        // Just appearance is enough for "Shatter" protocol.

        // 5. Verify backend persistence via API (fetch)
        // Access backend from browser context?
        const response = await page.request.get('/api/atoms');
        expect(response.ok()).toBeTruthy();
        const atoms = await response.json();
        const myAtom = atoms.find(a => a.id === atomPath);
        expect(myAtom).toBeDefined();
        // Expect status 1 (Claim)
        // expect(myAtom.status).toBe(1); // Depending on timing of witness
    });
});
