"""
test_runner.py — Single-file runner for all WorkForceIQ tests.
Run: python3 tests/test_runner.py

Generates: tests/report.html
Requires Flask app running at localhost:8080
"""
import subprocess, sys, os

def main():
    print("=" * 60)
    print("  WorkForceIQ — Selenium Test Suite")
    print("  Make sure Flask app is running: python3 app.py")
    print("=" * 60)
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--html=tests/report.html",
        "--self-contained-html",
        "-p", "no:warnings",
    ]
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
