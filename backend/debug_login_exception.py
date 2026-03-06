from fastapi.testclient import TestClient
from app.main import app


def main():
    client = TestClient(app, raise_server_exceptions=True)
    payload = {"email": "admin@testtrack.com", "password": "Admin@123"}

    try:
        response = client.post("/api/auth/login", json=payload)
        print("status", response.status_code)
        print("body", response.text)
    except Exception as exc:
        import traceback
        print("Exception raised by endpoint:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
