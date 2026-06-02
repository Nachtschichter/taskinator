import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  
  test('Login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/Taskinator/);
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });
  
  test('Login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Taskinator2026!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/board/);
    await expect(page.locator('text=Logout')).toBeVisible();
  });
  
  test('Login with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/login/);
  });
  
  test('Logout functionality', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Taskinator2026!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/board/);
    await expect(page.locator('text=Logout')).toBeVisible();
    await page.click('text=Logout');
    await page.waitForURL(/login/);
  });
  
L test('Protected page redirects to login', async ({ page }) => {
    await page.goto('/board');
    await page.waitForURL(/login/);
  });
});
