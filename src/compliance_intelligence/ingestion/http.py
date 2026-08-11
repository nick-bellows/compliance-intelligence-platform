from __future__ import annotations

import httpx

USER_AGENT = "compliance-intelligence-platform/0.1 (portfolio research project)"


def download_bytes(url: str, timeout_seconds: float = 120.0) -> bytes:
    response = httpx.get(
        url,
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.content
