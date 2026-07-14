from unittest.mock import patch


def test_verify_code_correct():
    with patch("app.auth.service.ACCESS_CODE", "secret123"):
        from app.auth.service import verify_code

        assert verify_code("secret123") is True


def test_verify_code_wrong():
    with patch("app.auth.service.ACCESS_CODE", "secret123"):
        from app.auth.service import verify_code

        assert verify_code("wrong") is False
