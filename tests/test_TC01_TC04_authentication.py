"""
Authentication Suite  —  TC-01 to TC-04
Matches PDF: Authentication Suite section exactly.
"""
import time, pytest
from selenium.webdriver.common.by import By
from tests.conftest import Page, CREDS

# TC-01 ───────────────────────────────────────────────────────────────────────
def test_TC01_login_with_valid_credentials(fresh_driver):
    """
    TC-01 | Module: Authentication
    Description: Verify login using correct username and password.
    Steps: Open login → enter valid creds → click Login
    Expected: User successfully redirected to their dashboard.
    Priority: High
    """
    p = Page(fresh_driver)
    p.login(*CREDS["hr"])
    assert "dashboard" in p.url, f"Expected dashboard, got: {p.url}"
    p.logout()

# TC-02 ───────────────────────────────────────────────────────────────────────
def test_TC02_login_with_invalid_password(fresh_driver):
    """
    TC-02 | Module: Authentication
    Description: Verify login fails with wrong password.
    Steps: Open login → enter valid username → enter WRONG password → click Login
    Expected: System shows 'Invalid Credentials' error, stays on login page.
    Priority: High
    """
    p = Page(fresh_driver)
    p.go("/login")
    p.fill(By.NAME, "username", CREDS["hr"][0])
    p.fill(By.NAME, "password", "WrongPassword_999!")
    p.click(By.CSS_SELECTOR, "button[type='submit']")
    time.sleep(0.5)
    assert "/login" in p.url or p.has("invalid") or p.has("incorrect"), \
        "Wrong password must show error and stay on login"

# TC-03 ───────────────────────────────────────────────────────────────────────
def test_TC03_login_with_empty_fields(fresh_driver):
    """
    TC-03 | Module: Authentication
    Description: Verify login is blocked when username and password are blank.
    Steps: Open login → leave both fields empty → click Login
    Expected: System shows validation message, does not proceed.
    Priority: Medium
    """
    p = Page(fresh_driver)
    p.go("/login")
    p.click(By.CSS_SELECTOR, "button[type='submit']")
    time.sleep(0.3)
    # HTML5 required attribute blocks submit OR server returns error
    assert "/login" in p.url, "Empty fields must not log in"

# TC-04 ───────────────────────────────────────────────────────────────────────
def test_TC04_session_timeout_after_logout(fresh_driver):
    """
    TC-04 | Module: Authentication
    Description: After logout, accessing a protected page redirects to login.
    Steps: Login → Logout → Navigate directly to /employee/dashboard
    Expected: Redirected to login page (session expired).
    Priority: Medium
    """
    p = Page(fresh_driver)
    p.login(*CREDS["employee"])
    p.logout()
    p.go("/employee/dashboard")
    time.sleep(0.4)
    assert "/login" in p.url, \
        f"After logout, protected page must redirect to login. Got: {p.url}"
