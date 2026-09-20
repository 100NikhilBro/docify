import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

security = HTTPBearer(auto_error=False)

# Maintain a global PyJWKClient instance to fetch and cache Clerk's public keys
jwk_client = None
CLERK_JWKS_URL = None


def get_jwk_client():
    global jwk_client, CLERK_JWKS_URL
    if jwk_client is None:
        CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
        if CLERK_JWKS_URL:
            jwk_client = jwt.PyJWKClient(CLERK_JWKS_URL)
    return jwk_client


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _mock_auth_allowed() -> bool:
    """Mock tokens are only for local development / tests."""
    if _env_flag("ALLOW_MOCK_AUTH"):
        return True
    # Default deny when NODE_ENV is unset (safer for misconfigured deploys)
    node_env = os.getenv("NODE_ENV", "").strip().lower()
    return node_env in {"development", "test", "dev"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    FastAPI dependency to extract and verify the Clerk user_id from the Authorization header.

    Missing or invalid credentials always return 401. There is no anonymous default_tenant
    fallback. Mock tokens are accepted only when ALLOW_MOCK_AUTH is set or NODE_ENV is
    development/test.
    """
    if not credentials or not credentials.credentials:
        raise _unauthorized("Authentication required")

    token = credentials.credentials

    # Handle mock tokens for unit testing / local verification (gated)
    if token == "invalid_mock_token":
        if not _mock_auth_allowed():
            raise _unauthorized("Mock authentication is disabled")
        raise HTTPException(
            status_code=status.HTTP_418_IM_A_TEAPOT,
            detail="Invalid authentication token: mock rejection",
        )

    if token == "mock_test_token" or token.startswith("mock_"):
        if not _mock_auth_allowed():
            raise _unauthorized("Mock authentication is disabled")
        if token == "mock_test_token":
            return "mock_user_id"
        return token.replace("mock_", "", 1)

    client = get_jwk_client()
    if not CLERK_JWKS_URL or not client:
        raise _unauthorized("Authentication is not configured (CLERK_JWKS_URL missing)")

    try:
        signing_key = client.get_signing_key_from_jwt(token)

        decode_kwargs = {
            "algorithms": ["RS256"],
            "options": {"verify_aud": False},
        }
        audience = os.getenv("CLERK_JWT_AUD", "").strip()
        if audience:
            decode_kwargs["audience"] = audience
            decode_kwargs["options"] = {"verify_aud": True}

        payload = jwt.decode(
            token,
            signing_key.key,
            **decode_kwargs,
        )
        user_id = payload.get("sub")
        if not user_id:
            raise _unauthorized("Token is missing subject claim ('sub')")
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        raise _unauthorized(f"Invalid authentication token: {str(e)}")
