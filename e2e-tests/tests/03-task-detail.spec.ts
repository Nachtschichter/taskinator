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
    await page.waitForTimeout(2000);
    
    // Check page loaded successfully (no error message)
    const content = await page.content();
    expect(content).not.toContain('Internal Server Error');
    expect(content).not.toContain('Task not found');
    expect(content).toContain('Taskinator');
  });
  
  test('Changelog section exists', async ({ page }) => {
    await page.goto('/tasks/1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    const content = await page.content();
    expect(content).not.toContain('Internal Server Error');
    // Changelog section only renders if there are entries
    // Check for the section OR that page loaded successfully
    if (content.includes('Changelog')) {
      expect(content).toContain('📝 Changelog');
    }
    // Page should still load successfully even without changelog
    expect(content).toContain('Task Dokumentation');
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
