import ssl

import httpx
import pytest

from scripts import check_emudhra


def certificate_rejection():
    error = httpx.ConnectError("certificate verification failed")
    error.__cause__ = ssl.SSLCertVerificationError(1, "certificate verify failed")
    return error


@pytest.fixture
def rejecting_client(monkeypatch):
    monkeypatch.setattr(check_emudhra.certifi, "__version__", "2026.10.19")

    def get(url, **kwargs):
        if url == check_emudhra.CONTROL_URL:
            return httpx.Response(200)
        raise certificate_rejection()

    monkeypatch.setattr(check_emudhra.httpx, "get", get)
    return get


def test_patched_bundle_and_both_certificate_rejections_pass(rejecting_client):
    assert check_emudhra.main() == 0


def test_old_bundle_fails_even_if_endpoints_are_rejected(rejecting_client, monkeypatch):
    monkeypatch.setattr(check_emudhra.certifi, "__version__", "2026.9.1")
    assert check_emudhra.main() == 1


@pytest.mark.parametrize("status", [200, 301, 404, 500])
def test_any_http_response_from_either_endpoint_fails(rejecting_client, monkeypatch, status):
    def get(url, **kwargs):
        if url == check_emudhra.TEST_URLS[1]:
            return httpx.Response(status)
        return rejecting_client(url, **kwargs)

    monkeypatch.setattr(check_emudhra.httpx, "get", get)
    assert check_emudhra.main() == 1


@pytest.mark.parametrize("error", [httpx.ConnectError("DNS failed"), httpx.ReadTimeout("timeout")])
def test_network_failure_is_not_a_certificate_rejection(rejecting_client, monkeypatch, error):
    def get(url, **kwargs):
        if url == check_emudhra.TEST_URLS[0]:
            raise error
        return rejecting_client(url, **kwargs)

    monkeypatch.setattr(check_emudhra.httpx, "get", get)
    assert check_emudhra.main() == 1


def test_failed_control_connection_prevents_pass(rejecting_client, monkeypatch):
    def get(url, **kwargs):
        if url == check_emudhra.CONTROL_URL:
            raise certificate_rejection()
        return rejecting_client(url, **kwargs)

    monkeypatch.setattr(check_emudhra.httpx, "get", get)
    assert check_emudhra.main() == 1


def test_generic_ssl_error_is_not_a_certificate_verification_error():
    assert not check_emudhra.is_certificate_error(ssl.SSLError("handshake failed"))
