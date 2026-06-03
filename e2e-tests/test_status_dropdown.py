"""
E2E Tests für Status-Dropdown Feature (Task #11)

Testet:
- Status-Wechsel zwischen allen Spalten
- Done-Validierung (kein Zurückschieben)
- UI-Elemente (Dropdown vorhanden)
- API-Responses
"""

import pytest
from playwright.sync_api import sync_playwright

import os
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:9900")
ADMIN_USER = "admin"
ADMIN_PASS = "***"

class TestStatusDropdown:
    """Testklasse für Status-Dropdown Feature"""
    
    @pytest.fixture(scope="class")
    def browser(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser
            browser.close()
    
    @pytest.fixture
    def page(self, browser):
        context = browser.new_context()
        page = context.new_page()
        
        # Login
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='username']", ADMIN_USER)
        page.fill("input[name='password']", ADMIN_PASS)
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/board")
        
        yield page
        context.close()
    
    def test_dropdown_exists_in_task_cards(self, page):
        """Test: Status-Dropdown ist in jeder Task-Karte vorhanden"""
        # Warte auf Board
        page.wait_for_selector(".board")
        
        # Prüfe ob Dropdowns existieren
        selects = page.query_selector_all(".status-select")
        assert len(selects) > 0, "Keine Status-Dropdowns gefunden"
        
        # Prüfe ob alle 4 Optionen vorhanden sind
        first_select = selects[0]
        options = first_select.query_selector_all("option")
        option_values = [opt.get_attribute("value") for opt in options]
        
        assert "BACKLOG" in option_values
        assert "TODO" in option_values
        assert "DOING" in option_values
        assert "DONE" in option_values
    
    def test_status_change_backlog_to_todo(self, page):
        """Test: Status-Wechsel Backlog → To Do"""
        # Finde erste Task in Backlog
        backlog_column = page.query_selector("#backlog")
        task_card = backlog_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in Backlog")
        
        # Ändere Status zu TODO
        select = task_card.query_selector(".status-select")
        select.select_option("TODO")
        
        # Warte auf Toast
        page.wait_for_selector(".toast.success")
        
        # Prüfe ob Task in To Do Spalte ist
        page.wait_for_timeout(500)  # Kurze Pause für DOM-Update
        todo_column = page.query_selector("#todo")
        task_id = task_card.get_attribute("data-task-id")
        moved_card = todo_column.query_selector(f".task-card[data-task-id='{task_id}']")
        
        assert moved_card is not None, "Task wurde nicht in To Do verschoben"
    
    def test_status_change_todo_to_doing(self, page):
        """Test: Status-Wechsel To Do → Doing"""
        # Finde erste Task in To Do
        todo_column = page.query_selector("#todo")
        task_card = todo_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in To Do")
        
        # Ändere Status zu DOING
        select = task_card.query_selector(".status-select")
        select.select_option("DOING")
        
        # Warte auf Toast
        page.wait_for_selector(".toast.success")
        
        # Prüfe ob Task in Doing Spalte ist
        page.wait_for_timeout(500)
        doing_column = page.query_selector("#doing")
        task_id = task_card.get_attribute("data-task-id")
        moved_card = doing_column.query_selector(f".task-card[data-task-id='{task_id}']")
        
        assert moved_card is not None, "Task wurde nicht in Doing verschoben"
    
    def test_status_change_doing_to_done(self, page):
        """Test: Status-Wechsel Doing → Done"""
        # Finde erste Task in Doing
        doing_column = page.query_selector("#doing")
        task_card = doing_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in Doing")
        
        # Ändere Status zu DONE
        select = task_card.query_selector(".status-select")
        select.select_option("DONE")
        
        # Warte auf Toast
        page.wait_for_selector(".toast.success")
        
        # Prüfe ob Task in Done Spalte ist
        page.wait_for_timeout(500)
        done_column = page.query_selector("#done")
        task_id = task_card.get_attribute("data-task-id")
        moved_card = done_column.query_selector(f".task-card[data-task-id='{task_id}']")
        
        assert moved_card is not None, "Task wurde nicht in Done verschoben"
        
        # Prüfe ob Dropdown disabled ist
        moved_select = moved_card.query_selector(".status-select")
        is_disabled = moved_select.is_disabled()
        assert is_disabled, "Dropdown sollte in Done disabled sein"
    
    def test_done_cannot_move_back(self, page):
        """Test: Done-Status kann nicht zurückgeschoben werden"""
        # Finde erste Task in Done
        done_column = page.query_selector("#done")
        task_card = done_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in Done")
        
        # Versuche Status zu ändern (sollte fehlschlagen)
        select = task_card.query_selector(".status-select")
        
        # Prüfe ob disabled
        is_disabled = select.is_disabled()
        assert is_disabled, "Done-Tasks sollten ein disabled Dropdown haben"
    
    def test_status_change_backwards(self, page):
        """Test: Status-Wechsel rückwärts (Doing → To Do)"""
        # Finde erste Task in Doing
        doing_column = page.query_selector("#doing")
        task_card = doing_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in Doing")
        
        # Ändere Status zu TODO
        select = task_card.query_selector(".status-select")
        select.select_option("TODO")
        
        # Warte auf Toast
        page.wait_for_selector(".toast.success")
        
        # Prüfe ob Task in To Do Spalte ist
        page.wait_for_timeout(500)
        todo_column = page.query_selector("#todo")
        task_id = task_card.get_attribute("data-task-id")
        moved_card = todo_column.query_selector(f".task-card[data-task-id='{task_id}']")
        
        assert moved_card is not None, "Task wurde nicht zurück nach To Do verschoben"
    
    def test_column_counts_update(self, page):
        """Test: Spaltenzähler aktualisieren sich nach Status-Wechsel"""
        # Lese aktuelle Counts
        backlog_count_before = page.inner_text("#backlog .count")
        todo_count_before = page.inner_text("#todo .count")
        
        # Finde Task in Backlog und verschiebe zu To Do
        backlog_column = page.query_selector("#backlog")
        task_card = backlog_column.query_selector(".task-card")
        
        if not task_card:
            pytest.skip("Keine Tasks in Backlog")
        
        select = task_card.query_selector(".status-select")
        select.select_option("TODO")
        
        # Warte auf Update
        page.wait_for_timeout(1000)
        
        # Prüfe ob Counts sich geändert haben
        backlog_count_after = page.inner_text("#backlog .count")
        todo_count_after = page.inner_text("#todo .count")
        
        assert backlog_count_after != backlog_count_before, "Backlog Count sollte sich ändern"
        assert todo_count_after != todo_count_before, "To Do Count sollte sich ändern"

class TestAPIEndpoints:
    """API-Tests für Status-Update Endpoint"""
    
    def test_api_status_update_success(self, page):
        """Test: API akzeptiert gültigen Status-Update"""
        # Login-Cookies holen
        cookies = page.context.cookies()
        
        # API-Request
        import requests
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        
        response = session.post(
            f"{BASE_URL}/tasks/1/move?ajax=1",
            data={"status": "TODO"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_api_done_cannot_move_back(self, page):
        """Test: API blockiert Zurückschieben aus Done"""
        # Annahme: Task 1 ist in Done
        cookies = page.context.cookies()
        
        import requests
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        
        response = session.post(
            f"{BASE_URL}/tasks/1/move?ajax=1",
            data={"status": "TODO"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert "DONE" in data["error"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])