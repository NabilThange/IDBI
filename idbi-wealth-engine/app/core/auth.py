"""
Simple API key gate.

Every /api route is protected by `require_api_key`. The expected key comes from the
API_KEY environment variable. Requests must send it via the `X-API-Key` header.

Dev fallback: if API_KEY is not set at all, the gate is disabled (open API) so local
development works without a key. In production ALWAYS set API_KEY so the gate is enforced.
"""

import os

from fastapi import Header, HTTPException, status


def require_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected = os.getenv("API_KEY", "")
    if not expected:
        # No key configured -> leave the API open (local/dev convenience).
        return
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
