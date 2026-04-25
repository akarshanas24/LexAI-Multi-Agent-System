"""tests/test_auth.py — Authentication endpoint tests"""
import pytest


@pytest.mark.asyncio
class TestRegister:

    async def test_register_success(self, client):
        r = await client.post("/auth/register", json={"username":"newuser","email":"new@lexai.dev","password":"securepass123"})
        assert r.status_code == 201
        d = r.json()
        assert d["username"] == "newuser"
        assert "password" not in d

    async def test_duplicate_username(self, client):
        r = await client.post("/auth/register", json={"username":"testuser","email":"x@x.com","password":"securepass123"})
        assert r.status_code == 400
        assert "Username" in r.json()["detail"]

    async def test_duplicate_email(self, client):
        r = await client.post("/auth/register", json={"username":"other","email":"test@lexai.dev","password":"securepass123"})
        assert r.status_code == 400
        assert "Email" in r.json()["detail"]

    async def test_short_password(self, client):
        r = await client.post("/auth/register", json={"username":"u","email":"u@u.com","password":"abc"})
        assert r.status_code == 400
        assert "8 characters" in r.json()["detail"]

    async def test_invalid_email(self, client):
        r = await client.post("/auth/register", json={"username":"u2","email":"bad-email","password":"securepass123"})
        assert r.status_code == 422


@pytest.mark.asyncio
class TestLogin:

    async def test_login_success(self, client):
        r = await client.post("/auth/login", data={"username":"testuser","password":"testpass123"})
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d
        assert d["token_type"] == "bearer"

    async def test_wrong_password(self, client):
        r = await client.post("/auth/login", data={"username":"testuser","password":"wrong"})
        assert r.status_code == 401

    async def test_unknown_user(self, client):
        r = await client.post("/auth/login", data={"username":"ghost","password":"x"})
        assert r.status_code == 401


@pytest.mark.asyncio
class TestMe:

    async def test_me_authenticated(self, auth_client):
        r = await auth_client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    async def test_me_unauthenticated(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401
