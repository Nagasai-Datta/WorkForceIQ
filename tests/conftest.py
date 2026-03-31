"""
conftest.py  —  Pytest + Selenium setup for WorkForceIQ

What Selenium does here (plain English):
  We write Python code that opens Chrome, clicks buttons, fills forms,
  and checks what appears on screen — automatically. It is NOT the
  Chrome extension (Selenium IDE). That's just a recorder. We use the
  Python library that directly controls Chrome via its DevTools protocol.

Mac setup (you already have Chrome — no manual chromedriver download needed):
  pip install selenium webdriver-manager pytest pytest-html
  webdriver-manager automatically downloads the right chromedriver for
  whichever version of Chrome you already have. Zero manual steps.

Run tests (Flask app must be running in another terminal first):
  Terminal 1:  python3 app.py
  Terminal 2:  pytest tests/ -v --html=tests/report.html
"""
import pytest, time, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:8080"

# Credentials that must exist after running seed_passwords.py
CREDS = {
    "admin":    ("admin",  "Admin@123"),
    "hr":       ("hr1",    "Hr@123456"),
    "pm":       ("pm1",    "Pm@123456"),
    "employee": ("emp1",   "Emp@123456"),
}

def _make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless")               # no GUI window
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-gpu")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        # Auto-downloads chromedriver that matches your installed Chrome
        svc = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=svc, options=opts)
    except Exception:
        return webdriver.Chrome(options=opts)     # chromedriver already on PATH

@pytest.fixture()
def fresh_driver():
    """Each test gets its own clean browser (no shared login state)."""
    d = _make_driver()
    d.implicitly_wait(6)
    yield d
    d.quit()

# ── Page helper ───────────────────────────────────────────────────────────────
class Page:
    def __init__(self, driver):
        self.d   = driver
        self.w   = WebDriverWait(driver, 10)

    def go(self, path):
        self.d.get(f"{BASE_URL}{path}")

    def fill(self, by, val, text):
        el = self.w.until(EC.presence_of_element_located((by, val)))
        el.clear(); el.send_keys(text)

    def click(self, by, val):
        self.w.until(EC.element_to_be_clickable((by, val))).click()

    def login(self, username, password):
        self.go("/login")
        self.fill(By.NAME, "username", username)
        self.fill(By.NAME, "password", password)
        self.click(By.CSS_SELECTOR, "button[type='submit']")
        time.sleep(0.6)

    def logout(self):
        self.go("/logout")

    def src(self) -> str:
        return self.d.page_source.lower()

    def has(self, text) -> bool:
        return text.lower() in self.src()

    @property
    def url(self):
        return self.d.current_url
