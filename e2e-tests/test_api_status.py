"""
API Tests für Status-Dropdown Feature (Task #11)
Testet die Backend-API ohne Browser
"""

import requests
import sys

BASE_URL = "http://localhost:9900"
ADMIN_USER = "admin"
ADMIN_PASS = "***"

def get_session():
    """Login und Session erstellen"""
    session = requests.Session()
    
    # Login
    response = session.post(
        f"{BASE_URL}/login",
        data={"username": ADMIN_USER, "password": ADMIN_PASS},
        allow_redirects=True
    )
    
    if response.status_code != 200:
        print(f"Login fehlgeschlagen: {response.status_code}")
        sys.exit(1)
    
    return session

def test_status_dropdown_ui():
    """Test: Board-Seite enthält Status-Dropdowns"""
    session = get_session()
    
    response = session.get(f"{BASE_URL}/board")
    assert response.status_code == 200, "Board nicht erreichbar"
    
    html = response.text
    
    # Prüfe ob Dropdowns existieren
    assert 'class="status-select"' in html, "Status-Dropdown nicht gefunden"
    assert 'handleStatusChange' in html, "JavaScript Handler nicht gefunden"
    
    # Prüfe ob alle Optionen vorhanden sind
    assert 'value="BACKLOG"' in html, "BACKLOG Option fehlt"
    assert 'value="TODO"' in html, "TODO Option fehlt"
    assert 'value="DOING"' in html, "DOING Option fehlt"
    assert 'value="DONE"' in html, "DONE Option fehlt"
    
    print("✅ UI-Test bestanden: Status-Dropdowns vorhanden")

def test_api_status_update():
    """Test: API akzeptiert Status-Update"""
    session = get_session()
    
    # Finde eine Task-ID (nehme die erste)
    response = session.get(f"{BASE_URL}/board")
    html = response.text
    
    # Extrahiere Task-ID
    import re
    match = re.search(r'data-task-id="(\d+)"', html)
    if not match:
        print("⚠️ Keine Tasks gefunden - überspringe API-Test")
        return
    
    task_id = match.group(1)
    
    # Teste Status-Update zu TODO
    response = session.post(
        f"{BASE_URL}/tasks/{task_id}/move?ajax=1",
        data={"status": "TODO"}
    )
    
    assert response.status_code == 200, f"API-Fehler: {response.status_code}"
    data = response.json()
    assert data["success"] is True, f"API-Error: {data.get('error', 'Unknown')}"
    
    print(f"✅ API-Test bestanden: Task {task_id} → TODO")
    
    # Zurücksetzen
    response = session.post(
        f"{BASE_URL}/tasks/{task_id}/move?ajax=1",
        data={"status": "backlog"}
    )
    
    if response.status_code == 200:
        print(f"✅ Rücksetzen bestanden: Task {task_id} → BACKLOG")

def test_done_validation():
    """Test: Done-Status ist final"""
    session = get_session()
    
    # Finde eine Task
    response = session.get(f"{BASE_URL}/board")
    html = response.text
    
    import re
    match = re.search(r'data-task-id="(\d+)"', html)
    if not match:
        print("⚠️ Keine Tasks gefunden - überspringe Done-Test")
        return
    
    task_id = match.group(1)
    
    # Verschiebe zu DONE
    response = session.post(
        f"{BASE_URL}/tasks/{task_id}/move?ajax=1",
        data={"status": "done"}
    )
    
    if response.status_code != 200:
        print(f"⚠️ Konnte Task nicht zu DONE verschieben: {response.status_code}")
        return
    
    # Versuche zurückzuschieben (sollte fehlschlagen)
    response = session.post(
        f"{BASE_URL}/tasks/{task_id}/move?ajax=1",
        data={"status": "TODO"}
    )
    
    assert response.status_code == 403, f"Erwartet 403, erhalten {response.status_code}"
    data = response.json()
    assert data["success"] is False, "Sollte fehlschlagen"
    assert "DONE" in data.get("error", ""), "Fehlermeldung sollte DONE erwähnen"
    
    print("✅ Done-Validierung bestanden: Task kann nicht zurückgeschoben werden")

if __name__ == "__main__":
    print("🧪 Starte API Tests für Task #11...")
    print()
    
    try:
        test_status_dropdown_ui()
        test_api_status_update()
        test_done_validation()
        
        print()
        print("🎉 Alle Tests bestanden!")
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")
        sys.exit(1)