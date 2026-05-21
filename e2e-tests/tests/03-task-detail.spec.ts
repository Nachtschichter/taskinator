import { test, expect } from '@playwright/test';

test.describe('Task Detail Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', process.env.ADMIN_PASSWORD || 'admin');
    await page.click('button[type="submit"]');
    await page.waitForURL(/board/);
  });
  
  test('Task detail page loads', async ({ page }) => {
    // Navigate directly to task detail page (task ID 1 from sample data)
    await page.goto('/tasks/1');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/tasks\/1/);
    await expect(page.locator('body')).toBeVisible();
  });
  
  test('Task details are displayed', async ({ page }) => {
    await page.goto('/tasks/1');
    await page.waitForLoadState('networkidle');
    
    // Check for priority badge in task-meta section
    await expect(page.locator('.task-meta')).toBeVisible();
    await expect(page.locator('text=priority')).toBeVisible();
    await expect(page.locator('.detail-label:has-text("Beschreibung")')).toBeVisible();
  });
  
  test('Changelog section exists', async ({ page }) => {
    await page.goto('/tasks/1');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h2:has-text("📝 Changelog")')).toBeVisible();
  });
  
  test('Documentation is read-only', async ({ page }) => {
    const firstTask = page.locator('.task-card a[href^="/tasks/"]').first();
    await firstTask.click();
    await page.waitForURL(/tasks\/\d+/);
    
    const textarea = page.locator('textarea[name="documentation"]');
    const count = await textarea.count();
    
    // Should be 0 (read-only display, no edit form)
    expect(count).toBe(0);
  });
});
