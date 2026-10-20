"""Tests for the JWT exp decoder.  Run with: python -m unittest discover -s tests"""

import base64
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibkr_to_ghostfolio import jwt_expiry, warn_static_token_expiry  # noqa: E402


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_token(claims):
    """Build an unsigned JWT-shaped string with the given payload claims."""
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps(claims).encode())
    return f"{header}.{payload}.signature"


class JwtExpiryTest(unittest.TestCase):
    def test_future_exp(self):
        exp = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=180)
        token = make_token({"id": "user", "exp": int(exp.timestamp())})
        self.assertEqual(jwt_expiry(token), exp)
        with self.assertLogs(level="WARNING") as logs:
            warn_static_token_expiry(token)
        self.assertIn("days remaining", logs.output[0])
        self.assertNotIn(token, logs.output[0])

    def test_expired_exp(self):
        exp = datetime(2026, 9, 22, 8, 30, tzinfo=timezone.utc)
        token = make_token({"id": "user", "exp": int(exp.timestamp())})
        self.assertEqual(jwt_expiry(token), exp)
        with self.assertLogs(level="WARNING") as logs:
            warn_static_token_expiry(token)
        self.assertIn("expired on 2026-09-22T08:30:00+00:00", logs.output[0])
        self.assertNotIn(token, logs.output[0])

    def test_non_jwt(self):
        for token in ("not-a-jwt", "a.b.c", "", make_token({"id": "no-exp"})):
            self.assertIsNone(jwt_expiry(token), token)
        with self.assertLogs(level="WARNING") as logs:
            warn_static_token_expiry("not-a-jwt")
        self.assertIn("expiry is unknown", logs.output[0])


if __name__ == "__main__":
    unittest.main()
