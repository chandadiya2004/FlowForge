"""End-to-end verification script for Milestone 2 (Auth & RBAC)."""

import os
import sys
import subprocess
import time
import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 2 E2E Verification ===")

    # 1. Health check
    res = httpx.get(f"{SERVER_URL}/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] GET /health -> 200 OK")

    # 2. Register member
    member_email = "member@flowforge.dev"
    member_pw = "Password123!"
    reg_payload = {"email": member_email, "password": member_pw}
    res = httpx.post(f"{SERVER_URL}/auth/register", json=reg_payload)
    if res.status_code == 409:
        print("[INFO] User already exists from previous run, proceeding to login...")
    else:
        assert res.status_code == 201, f"Registration failed: {res.text}"
        data = res.json()
        assert data["email"] == member_email
        assert data["role"] == "member"
        assert "hashed_password" not in data
        print("[PASS] POST /auth/register -> 201 Created (role: member, no hashed_password exposed)")

    # 3. Duplicate registration check (409)
    res = httpx.post(f"{SERVER_URL}/auth/register", json=reg_payload)
    assert res.status_code == 409, f"Duplicate check failed: {res.text}"
    print("[PASS] POST /auth/register (duplicate email) -> 409 Conflict")

    # 4. Login
    res = httpx.post(f"{SERVER_URL}/auth/login", json={"email": member_email, "password": member_pw})
    assert res.status_code == 200, f"Login failed: {res.text}"
    tokens = res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    print("[PASS] POST /auth/login -> 200 OK (received access and refresh tokens)")

    # 5. Call /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    res = httpx.get(f"{SERVER_URL}/auth/me", headers=headers)
    assert res.status_code == 200, f"/auth/me failed: {res.text}"
    user_me = res.json()
    assert user_me["email"] == member_email
    print(f"[PASS] GET /auth/me -> 200 OK (id: {user_me['id']}, email: {user_me['email']}, role: {user_me['role']})")

    # 6. Call /admin-check with member token (expect 403)
    res = httpx.get(f"{SERVER_URL}/admin-check", headers=headers)
    assert res.status_code == 403, f"/admin-check expected 403 but got {res.status_code}: {res.text}"
    print(f"[PASS] GET /admin-check with Member token -> 403 Forbidden ({res.json()['detail']})")

    # 7. Call /auth/refresh
    res = httpx.post(f"{SERVER_URL}/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200, f"/auth/refresh failed: {res.text}"
    new_access_token = res.json()["access_token"]
    res = httpx.get(f"{SERVER_URL}/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert res.status_code == 200
    print("[PASS] POST /auth/refresh -> 200 OK (new access token verified on /auth/me)")

    print("\n>>> ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    main()
