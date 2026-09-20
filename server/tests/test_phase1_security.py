"""Phase 1 security unit tests — auth, paths, job ACL."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Ensure server/ is on the path before imports
SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

# Stub optional heavy deps so upload.py can be imported for job ACL tests
for _mod in ("yt_dlp", "imageio_ffmpeg"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestAuth(unittest.TestCase):
    def setUp(self):
        # Reset JWKS client cache between tests
        import app.api.auth as auth_mod

        auth_mod.jwk_client = None
        auth_mod.CLERK_JWKS_URL = None

    def test_missing_credentials_returns_401(self):
        from app.api.auth import get_current_user

        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_empty_token_returns_401(self):
        from app.api.auth import get_current_user

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(creds)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_mock_token_allowed_in_development(self):
        from app.api.auth import get_current_user

        with patch.dict(os.environ, {"NODE_ENV": "development"}, clear=False):
            os.environ.pop("ALLOW_MOCK_AUTH", None)
            # Force re-read of env inside helpers; NODE_ENV already set
            creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="mock_test_token"
            )
            self.assertEqual(get_current_user(creds), "mock_user_id")

            creds2 = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="mock_alice"
            )
            self.assertEqual(get_current_user(creds2), "alice")

    def test_mock_token_blocked_in_production(self):
        from app.api.auth import get_current_user

        env = {
            "NODE_ENV": "production",
            "ALLOW_MOCK_AUTH": "",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("ALLOW_MOCK_AUTH", None)
            with patch.dict(os.environ, {"NODE_ENV": "production"}, clear=False):
                creds = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials="mock_test_token"
                )
                with self.assertRaises(HTTPException) as ctx:
                    get_current_user(creds)
                self.assertEqual(ctx.exception.status_code, 401)

    def test_mock_allowed_via_explicit_flag_in_production(self):
        from app.api.auth import get_current_user

        with patch.dict(
            os.environ,
            {"NODE_ENV": "production", "ALLOW_MOCK_AUTH": "true"},
            clear=False,
        ):
            creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="mock_test_token"
            )
            self.assertEqual(get_current_user(creds), "mock_user_id")

    def test_audience_verified_when_clerk_jwt_aud_set(self):
        from app.api.auth import get_current_user
        import app.api.auth as auth_mod

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value.key = "secret"

        with patch.dict(
            os.environ,
            {
                "NODE_ENV": "production",
                "CLERK_JWKS_URL": "https://example.com/.well-known/jwks.json",
                "CLERK_JWT_AUD": "docify-api",
            },
            clear=False,
        ):
            os.environ.pop("ALLOW_MOCK_AUTH", None)
            auth_mod.jwk_client = mock_client
            auth_mod.CLERK_JWKS_URL = os.environ["CLERK_JWKS_URL"]

            with patch("app.api.auth.jwt.decode", return_value={"sub": "user_123"}) as decode:
                creds = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials="real.jwt.token"
                )
                self.assertEqual(get_current_user(creds), "user_123")
                _, kwargs = decode.call_args
                self.assertEqual(kwargs.get("audience"), "docify-api")
                self.assertEqual(kwargs.get("options"), {"verify_aud": True})

    def test_missing_jwks_returns_401(self):
        from app.api.auth import get_current_user
        import app.api.auth as auth_mod

        with patch.dict(os.environ, {"NODE_ENV": "production"}, clear=False):
            os.environ.pop("ALLOW_MOCK_AUTH", None)
            os.environ.pop("CLERK_JWKS_URL", None)
            auth_mod.jwk_client = None
            auth_mod.CLERK_JWKS_URL = None
            creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="eyJhbGciOiJSUzI1NiJ9.e30.x"
            )
            with self.assertRaises(HTTPException) as ctx:
                get_current_user(creds)
            self.assertEqual(ctx.exception.status_code, 401)


class TestPaths(unittest.TestCase):
    def test_sanitize_rejects_empty_and_dot_segments(self):
        from app.api.paths import sanitize_filename

        for bad in ["", ".", "..", "   "]:
            with self.assertRaises(HTTPException) as ctx:
                sanitize_filename(bad)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_sanitize_collapses_traversal_to_basename(self):
        from app.api.paths import sanitize_filename

        # Traversal prefixes must not escape; only the leaf name is kept
        self.assertEqual(sanitize_filename("../secret.pdf"), "secret.pdf")
        self.assertEqual(sanitize_filename("..\\secret.pdf"), "secret.pdf")
        self.assertEqual(sanitize_filename("/etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("report.pdf"), "report.pdf")
        self.assertEqual(sanitize_filename("foo/../report.pdf"), "report.pdf")

    def test_resolve_stays_under_user_dir(self):
        from app.api.paths import resolve_under_user_dir, sanitize_filename

        with tempfile.TemporaryDirectory() as tmp:
            user_root = os.path.join(tmp, "cleaned_pdfs")
            os.makedirs(os.path.join(user_root, "user_a"), exist_ok=True)
            safe = sanitize_filename("doc.pdf")
            resolved = resolve_under_user_dir(user_root, "user_a", filename=safe)
            self.assertTrue(resolved.startswith(os.path.abspath(user_root)))
            self.assertTrue(resolved.endswith(os.path.join("user_a", "doc.pdf")))

    def test_resolve_rejects_user_id_traversal(self):
        from app.api.paths import resolve_under_user_dir

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(HTTPException):
                resolve_under_user_dir(tmp, "../../etc", filename="passwd")

    def test_resolve_blocks_escape_even_if_joined_unsafely(self):
        """Defense in depth: resolved path must remain under the tenant root."""
        from app.api.paths import resolve_under_user_dir

        with tempfile.TemporaryDirectory() as tmp:
            victim = os.path.join(tmp, "cleaned_pdfs", "user_b")
            os.makedirs(victim, exist_ok=True)
            open(os.path.join(victim, "secret.pdf"), "w").close()

            # Sanitized leaf cannot reach user_b from user_a
            resolved = resolve_under_user_dir(
                os.path.join(tmp, "cleaned_pdfs"),
                "user_a",
                filename="secret.pdf",
            )
            self.assertIn(os.path.join("user_a", "secret.pdf"), resolved)
            self.assertNotIn(os.path.join("user_b", "secret.pdf"), resolved)

class TestJobAcl(unittest.TestCase):
    def setUp(self):
        from app.api.upload import job_store, Job, JobStatus

        job_store.clear()
        self.Job = Job
        self.JobStatus = JobStatus
        self.job_store = job_store

    def test_get_job_status_only_owner(self):
        from app.api.upload import get_job_status

        job = self.Job(job_id="j1", filename="a.pdf", user_id="user_a")
        self.job_store["j1"] = job

        ok = get_job_status("j1", user_id="user_a")
        self.assertEqual(ok.status_code, 200)

        with self.assertRaises(HTTPException) as ctx:
            get_job_status("j1", user_id="user_b")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_all_jobs_no_cross_tenant(self):
        from app.api.upload import get_all_jobs
        import json

        self.job_store["j1"] = self.Job(job_id="j1", filename="a.pdf", user_id="user_a")
        self.job_store["j2"] = self.Job(job_id="j2", filename="b.pdf", user_id="user_b")

        resp = get_all_jobs(user_id="user_a")
        body = json.loads(resp.body.decode())
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["job_id"], "j1")

        # Former default_tenant privilege must not list other users' jobs
        resp_default = get_all_jobs(user_id="default_tenant")
        body_default = json.loads(resp_default.body.decode())
        self.assertEqual(body_default, [])


if __name__ == "__main__":
    unittest.main()
