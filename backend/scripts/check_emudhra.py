"""Run with the deployed backend's Python: python scripts/check_emudhra.py."""

import os
import ssl

import certifi
import httpx


MIN_CERTIFI = (2026, 10, 19)
TEST_URLS = (
    "https://dv-g3b-emudhra.we-have-a-problem.com/",
    "https://dv-g3b-aaa-emudhra.we-have-a-problem.com/",
)
CONTROL_URL = "https://catalog.calpoly.edu/"


def is_certificate_error(error: BaseException) -> bool:
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, ssl.SSLCertVerificationError):
            return True
        error = error.__cause__ or error.__context__
    return False


def main() -> int:
    passed = True
    print(f"certifi: {certifi.__version__}")
    if tuple(int(part) for part in certifi.__version__.split(".")) < MIN_CERTIFI:
        print("FAIL: certifi must be 2026.10.19 or later.")
        passed = False

    for name in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
        if os.environ.get(name):
            print(f"NOTICE: {name} overrides the default CA bundle; testing with it enabled.")

    # Match the production httpx.get/post defaults, including proxy/CA environment
    # settings. Never pass application credentials to these public test endpoints.
    try:
        response = httpx.get(CONTROL_URL, timeout=15)
        print(f"PASS: control HTTPS connection succeeded (HTTP {response.status_code}).")
    except httpx.RequestError as error:
        print(f"INCONCLUSIVE: control HTTPS connection failed ({type(error).__name__}).")
        passed = False

    for url in TEST_URLS:
        try:
            response = httpx.get(url, timeout=15)
        except httpx.RequestError as error:
            if is_certificate_error(error):
                print(f"PASS: {url} rejected with a certificate verification error.")
            else:
                print(f"INCONCLUSIVE: {url} failed with {type(error).__name__}, not a certificate error.")
                passed = False
        else:
            print(f"FAIL: {url} was trusted (HTTP {response.status_code}).")
            passed = False

    if passed:
        print("PASS: this Python/HTTPX environment rejects both advisory test endpoints.")
    else:
        print("Protection is not confirmed. Resolve all FAIL/INCONCLUSIVE results and rerun.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
