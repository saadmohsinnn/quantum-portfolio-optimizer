#!/usr/bin/env python3
"""
Post-deployment verification script for QuanPort.
Run after deploying to Render: python verification.py https://your-app.onrender.com
"""

import sys
import urllib.request
import urllib.error


def test_endpoint(base_url: str, path: str, expected_status: int = 200) -> bool:
    """Return True if the endpoint returns expected_status."""
    url = base_url.rstrip("/") + path
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.getcode()
            if status == expected_status:
                print(f"  OK {path}: {status}")
                return True
            print(f"  FAIL {path}: got {status}, expected {expected_status}")
            return False
    except urllib.error.HTTPError as e:
        print(f"  FAIL {path}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  FAIL {path}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python verification.py <BASE_URL>")
        print("Example: python verification.py https://quanport.onrender.com")
        sys.exit(1)

    base_url = sys.argv[1]
    print(f"Verifying: {base_url}\n")

    ok = True
    ok &= test_endpoint(base_url, "/")
    ok &= test_endpoint(base_url, "/api/health")
    ok &= test_endpoint(base_url, "/api/symbols")
    ok &= test_endpoint(base_url, "/api/predefined")

    print()
    if ok:
        print("All checks passed.")
        sys.exit(0)
    else:
        print("Some checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
