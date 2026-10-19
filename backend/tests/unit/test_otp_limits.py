"""Review fix Important 6: OTP SMS requests are rate limited per phone and per IP (SMS pumping)."""
import random
from datetime import UTC, datetime, timedelta

from app.auth.otp_limits import PER_IP_PER_HOUR, PER_PHONE_PER_HOUR, check_and_record
from app.db import get_sessionmaker


async def test_per_phone_limit_and_window():
    now = datetime.now(UTC)
    async with get_sessionmaker()() as s:
        for i in range(PER_PHONE_PER_HOUR):
            assert await check_and_record(s, "+919820000001", f"10.0.0.{i}", now) is None
        assert "Too many" in await check_and_record(s, "+919820000001", "10.0.0.99", now)
        assert await check_and_record(s, "+919820000001", "10.0.0.99", now + timedelta(hours=1, minutes=1)) is None


async def test_per_ip_limit():
    now = datetime.now(UTC)
    async with get_sessionmaker()() as s:
        for i in range(PER_IP_PER_HOUR):
            assert await check_and_record(s, f"+91982000{i:04d}", "203.0.113.7", now) is None
        assert "Too many" in await check_and_record(s, "+919829999999", "203.0.113.7", now)


async def test_sixth_code_request_is_refused_by_the_real_endpoint(client):
    phone = f"+9198{random.randint(10000000, 99999999)}"
    statuses = []
    for _ in range(PER_PHONE_PER_HOUR + 1):
        res = await client.post("/api/v1/auth/signinup/code", json={"phoneNumber": phone}, headers={"st-auth-mode": "header"})
        statuses.append(res.json()["status"])
    assert statuses[:PER_PHONE_PER_HOUR] == ["OK"] * PER_PHONE_PER_HOUR
    assert statuses[-1] == "GENERAL_ERROR"
