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
    const firstTask = page.locator('.task-card a[href^="/tasks/"]').first();
    await firstTask.click();
    await page.waitForURL(/tasks\/\d+/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.container')).toBeVisible();
  });
  
  test('Task details are displayed', async ({ page }) => {
    const firstTask = page.locator('.task-card a[href^="/tasks/"]').first();
    await firstTask.click();
    await page.waitForURL(/tasks\/\d+/);
    await page.waitForLoadState('networkidle');
    
    await expect(page.locator('.badge')).toBeVisible();
    await expect(page.locator('.detail-label:has-text("Beschreibung")')).toBeVisible();
    await expect(page.locator('.detail-label:has-text("Erstellt")')).toBeVisible();
  });
  
  test('Changelog section exists', async ({ page }) => {
    const firstTask = page.locator('.task-card a[href^="/tasks/"]').first();
    await firstTask.click();
    await page.waitForURL(/tasks\/\d+/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.card:has-text("Changelog")')).toBeVisible();
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
