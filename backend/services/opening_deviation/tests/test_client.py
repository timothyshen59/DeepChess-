"""
LichessExplorerClient tests -- real `httpx.AsyncClient` headers/request
path, no real network. Uses `httpx.MockTransport` to intercept the actual
outgoing request and assert on its headers directly, rather than poking at
`_client.headers` after construction -- this proves what's genuinely sent
on a request, not just what was configured.
"""

from __future__ import annotations

import unittest

import httpx

from services.opening_deviation.config import OpeningDeviationSettings
from services.opening_deviation.explorer.client import LichessExplorerClient

FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _settings(**overrides) -> OpeningDeviationSettings:
    defaults = dict(explorer_base_url="https://explorer.lichess.ovh", explorer_dataset="masters")
    defaults.update(overrides)
    return OpeningDeviationSettings(**defaults)


def _swap_in_mock_transport(client: LichessExplorerClient, handler) -> None:
    """Test-only: replace the real network transport with a
    `MockTransport`, keeping the real headers `LichessExplorerClient`
    already configured on construction -- so the assertion is against
    what the class actually built, not a second hand-rolled client."""
    real_client = client._client  # noqa: SLF001 -- test-only introspection
    client._client = httpx.AsyncClient(
        base_url=real_client.base_url,
        headers=real_client.headers,
        transport=httpx.MockTransport(handler),
    )


def _empty_explorer_response(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"white": 0, "draws": 0, "black": 0, "moves": []})


class LichessExplorerClientAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_omits_authorization_header_when_no_token_configured(self) -> None:
        client = LichessExplorerClient(_settings(lichess_api_token=None))
        captured: dict[str, httpx.Headers] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return _empty_explorer_response(request)

        _swap_in_mock_transport(client, handler)

        try:
            await client.fetch(FEN)
        finally:
            await client.aclose()

        self.assertNotIn("authorization", captured["headers"])
        self.assertEqual(captured["headers"]["user-agent"], "DeepChess-OpeningDeviationEngine/1.0")

    async def test_includes_bearer_authorization_header_when_token_configured(self) -> None:
        client = LichessExplorerClient(_settings(lichess_api_token="test-token-123"))
        captured: dict[str, httpx.Headers] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return _empty_explorer_response(request)

        _swap_in_mock_transport(client, handler)

        try:
            await client.fetch(FEN)
        finally:
            await client.aclose()

        self.assertEqual(captured["headers"]["authorization"], "Bearer test-token-123")

    async def test_unauthenticated_request_still_succeeds(self) -> None:
        """The masters dataset works without a token (just rate-limited
        lower) -- adding auth support must not break that path."""
        client = LichessExplorerClient(_settings(lichess_api_token=None))
        _swap_in_mock_transport(client, lambda request: _empty_explorer_response(request))

        try:
            stats = await client.fetch(FEN)
        finally:
            await client.aclose()

        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_games, 0)


class LichessExplorerClientRateLimitTests(unittest.IsolatedAsyncioTestCase):
    """explorer_retry_backoff_seconds=0.0 and a "Retry-After: 0" header
    keep these tests instant -- no real waiting, no patching asyncio.sleep."""

    async def test_retries_after_429_and_succeeds(self) -> None:
        client = LichessExplorerClient(
            _settings(explorer_max_retries=2, explorer_retry_backoff_seconds=0.0)
        )
        attempts = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["count"] += 1
            if attempts["count"] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return _empty_explorer_response(request)

        _swap_in_mock_transport(client, handler)

        try:
            stats = await client.fetch(FEN)
        finally:
            await client.aclose()

        self.assertIsNotNone(stats)
        self.assertEqual(attempts["count"], 2)

    async def test_gives_up_after_max_retries_and_returns_none(self) -> None:
        client = LichessExplorerClient(
            _settings(explorer_max_retries=2, explorer_retry_backoff_seconds=0.0)
        )
        attempts = {"count": 0}

        def handler(_request: httpx.Request) -> httpx.Response:
            attempts["count"] += 1
            return httpx.Response(429, headers={"Retry-After": "0"})

        _swap_in_mock_transport(client, handler)

        try:
            stats = await client.fetch(FEN)
        finally:
            await client.aclose()

        self.assertIsNone(stats)
        self.assertEqual(attempts["count"], 3)  # initial attempt + 2 retries

    async def test_backs_off_exponentially_without_a_retry_after_header(self) -> None:
        client = LichessExplorerClient(
            _settings(explorer_max_retries=2, explorer_retry_backoff_seconds=0.0)
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429)  # no Retry-After header at all

        _swap_in_mock_transport(client, handler)

        try:
            stats = await client.fetch(FEN)
        finally:
            await client.aclose()

        # No Retry-After and a 0s backoff base -- still resolves (to None,
        # since every attempt 429s), just proving the no-header path
        # doesn't crash trying to parse a missing header.
        self.assertIsNone(stats)


if __name__ == "__main__":
    unittest.main()
