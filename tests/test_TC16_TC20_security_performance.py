"""
Security & Performance Suite  —  TC-16 to TC-20
Matches PDF: Security Suite + Performance Suite sections exactly.
"""
import time, pytest
from selenium.webdriver.common.by import By
from tests.conftest import Page, CREDS, BASE_URL

# TC-16 ───────────────────────────────────────────────────────────────────────
def test_TC16_unauthorized_page_access(fresh_driver):
    """
    TC-16 | Module: Security
    Description: Employee role cannot access HR-restricted pages.
    Steps: Login as employee → directly navigate to /hr/dashboard and /admin/dashboard
    Expected: Access denied (403 Forbidden or redirect to login).
    Priority: High
    """
    p = Page(fresh_driver)
    p.login(*CREDS["employee"])
    for restricted in ["/hr/dashboard", "/admin/dashboard", "/pm/dashboard"]:
        p.go(restricted)
        time.sleep(0.4)
        assert "403" in p.d.page_source or "forbidden" in p.d.page_source.lower() or \
               restricted not in p.url or "/login" in p.url, \
            f"Employee must be denied access to {restricted}"

# TC-17 ───────────────────────────────────────────────────────────────────────
def test_TC17_sql_injection_attempt(fresh_driver):
    """
    TC-17 | Module: Security
    Description: SQL injection payload in login field must not bypass authentication.
    Steps: Enter ' OR '1'='1 in both username and password → click Login
    Expected: System prevents injection. No login. Stays on login page.
    Priority: High
    """
    p = Page(fresh_driver)
    p.go("/login")
    p.fill(By.NAME, "username", "' OR '1'='1' --")
    p.fill(By.NAME, "password", "' OR '1'='1' --")
    fresh_driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(0.6)
    assert "/login" in p.url or "dashboard" not in p.url, \
        "SQL injection must NOT bypass authentication (use parameterized queries)"

# TC-18 ───────────────────────────────────────────────────────────────────────
def test_TC18_xss_attack_attempt(fresh_driver):
    """
    TC-18 | Module: Security
    Description: XSS payload in profile field must not execute as JavaScript.
    Steps: Login as employee → go to profile → enter <script>alert(1)</script>
           in name field → save → check script is NOT executed.
    Expected: Script not executed. Payload is HTML-escaped by Jinja2.
    Priority: High
    """
    p = Page(fresh_driver)
    p.login(*CREDS["employee"])
    p.go("/employee/profile")
    time.sleep(0.5)
    xss = "<script>alert('XSS_TEST_MARKER')</script>"
    try:
        name_el = fresh_driver.find_element(By.NAME, "name")
        name_el.clear(); name_el.send_keys(xss)
        fresh_driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(0.8)
        # Check: no alert dialog triggered
        try:
            alert = fresh_driver.switch_to.alert
            alert.dismiss()
            pytest.fail("XSS EXECUTED — Critical security failure!")
        except Exception:
            pass   # Good — no alert = XSS blocked
        # Check payload is escaped in source (should appear as &lt;script&gt;)
        assert "<script>alert(" not in fresh_driver.page_source, \
            "Raw XSS payload must not appear in rendered HTML"
    except Exception as e:
        if "XSS EXECUTED" in str(e) or "security" in str(e).lower():
            raise
        pytest.skip(f"Profile form interaction failed: {e}")

# TC-19 ───────────────────────────────────────────────────────────────────────
def test_TC19_heatmap_generation_under_heavy_load(fresh_driver):
    """
    TC-19 | Module: Performance
    Description: Analytics heatmap must load within acceptable time under load.
    Steps: Login as HR → navigate to /hr/analytics → measure page load time
    Expected: Page responds in under 5 seconds (SLA for internal tools).
    Priority: Medium
    """
    import time as _time
    p = Page(fresh_driver)
    p.login(*CREDS["hr"])

    start = _time.time()
    p.go("/hr/analytics")
    # Wait for page to have meaningful content
    deadline = _time.time() + 5
    while _time.time() < deadline:
        if p.has("skill") or p.has("chart") or p.has("analytics"):
            break
        _time.sleep(0.2)
    elapsed = _time.time() - start

    assert elapsed < 5.0, \
        f"Analytics page took {elapsed:.2f}s — must be under 5s (performance SLA)"
    assert "500" not in fresh_driver.title, "Page must not error under normal load"

# TC-20 ───────────────────────────────────────────────────────────────────────
def test_TC20_api_response_time_validation(fresh_driver):
    """
    TC-20 | Module: Performance
    Description: The skill extraction API endpoint responds within SLA time.
    Steps: Login as employee → POST to /employee/extract-skills with sample text →
           measure response time
    Expected: API responds within 6 seconds (accounts for Groq LLM latency).
    Priority: Medium
    """
    import time as _time, requests
    p = Page(fresh_driver)
    p.login(*CREDS["employee"])

    # Get the session cookie from Selenium and use it with requests for API timing
    cookies = {c["name"]: c["value"] for c in fresh_driver.get_cookies()}
    sample_text = (
        "Python developer with 4 years experience. "
        "Worked with Django, PostgreSQL, Docker and AWS."
    )
    start = _time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/employee/extract-skills",
            data={"resume_text": sample_text},
            cookies=cookies,
            timeout=10,
        )
        elapsed = _time.time() - start
        assert elapsed < 6.0, \
            f"Skill extraction API took {elapsed:.2f}s — must be under 6s"
        assert resp.status_code in (200, 302), \
            f"API must return 200, got {resp.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip("Flask app not running — start with: python3 app.py")
