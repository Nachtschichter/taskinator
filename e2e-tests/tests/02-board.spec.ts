import { test, expect } from '@playwright/test';

test.describe('Kanban Board AdminLTE 4', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'Taskinator2026!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/board/);
  });
  
  test('Board page loads with AdminLTE 4 layout', async ({ page }) => {
    await expect(page).toHaveURL(/board/);
    await expect(page.locator('.kanban-lane[data-status="backlog"]')).toBeVisible();
    await expect(page.locator('.kanban-lane[data-status="todo"]')).toBeVisible();
    await expect(page.locator('.kanban-lane[data-status="doing"]')).toBeVisible();
    await expect(page.locator('.kanban-lane[data-status="done"]')).toBeVisible();
  });
  
  test('Task cards are rendered', async ({ page }) => {
    const taskCards = page.locator('.task-card');
    const count = await taskCards.count();
    console.log(`Found ${count} task cards`);
    expect(count).toBeGreaterThan(0);
  });
  
  test('Create new task via AdminLTE modal', async ({ page }) => {
    await page.click('button:has-text("Add Task")');
    await page.waitForSelector('input[name="title"]');
    await page.fill('input[name="title"]', 'E2E Test Task AdminLTE');
    await page.fill('textarea[name="description"]', 'Created by E2E test AdminLTE');
    await page.selectOption('select[name="priority"]', 'MEDIUM');
    await page.selectOption('select[name="category"]', 'feature');
    await page.click('#btn-save-task');
    await page.waitForTimeout(2000);
    await expect(page.locator('text=E2E Test Task AdminLTE')).toBeVisible();
  });
  
  test('Drag and Drop functionality', async ({ page }) => {
    const backlogLane = page.locator('.kanban-lane[data-status="backlog"]');
    const firstTask = backlogLane.locator('.task-card').first();
    await expect(firstTask).toBeVisible();
    
    const todoLane = page.locator('.kanban-lane[data-status="todo"]');
    
    // Use Playwright to drag the task from Backlog to Todo
    await firstTask.dragTo(todoLane);
    
    await page.waitForTimeout(1000);
    
    // Verify task is now in Todo lane
    const movedTask = todoLane.locator('.task-card').filter({ hasText: await firstTask.locator('h6').textContent() });
    await expect(movedTask).toBeVisible();
    console.log('Drag and Drop test passed ✓');
  });
});
