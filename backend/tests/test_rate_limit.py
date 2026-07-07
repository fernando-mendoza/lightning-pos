"""Unit tests del rate limiter (sin HTTP; corre en el contenedor de tests)."""

import time

from infrastructure.security.rate_limit import RateLimiter, parse_limit


def test_parse_limit():
    assert parse_limit("20/60") == (20, 60.0)
    assert parse_limit("5/0.5") == (5, 0.5)
    assert parse_limit("10") == (10, 60.0)  # default 60s


def test_blocks_over_limit_and_isolates_keys():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert all(rl.allow("a") for _ in range(3))
    assert rl.allow("a") is False  # cuarta en la ventana: bloqueada
    assert rl.allow("b") is True  # otra llave no se ve afectada


def test_window_slides():
    rl = RateLimiter(max_requests=2, window_seconds=0.05)
    assert rl.allow("k") and rl.allow("k")
    assert rl.allow("k") is False
    time.sleep(0.06)  # la ventana expira
    assert rl.allow("k") is True
