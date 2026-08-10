import os
import uuid
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load ENV from backend/.env
load_dotenv(dotenv_path="D:/Projects/Mercura/backend/.env")

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found.")
    exit(1)

engine = create_engine(db_url)

API_URL = "http://localhost:8000"

# Register a new user
unique_id = uuid.uuid4().hex[:6]
user_email = f"db_verify_{unique_id}@example.com"
user_password = "password123"
user_fullname = f"DB Verify {unique_id}"

print(f"Registering user via API: {user_email}")

res = requests.post(
    f"{API_URL}/auth/register",
    json={
        "email": user_email,
        "password": user_password,
        "full_name": user_fullname,
    },
)

if res.status_code != 200:
    print("Registration failed:", res.text)
    exit(1)

new_user_id = res.json()["id"]
print(f"User created via API with ID: {new_user_id}")
print("-" * 50)

with engine.connect() as conn:
    user_res = conn.execute(
        text("SELECT id, email, full_name FROM users WHERE email = :email"),
        {"email": user_email},
    ).fetchone()

    print("User:", user_res)

    member_res = conn.execute(
        text(
            "SELECT user_id, business_id, role FROM business_members WHERE user_id = :user_id"
        ),
        {"user_id": new_user_id},
    ).fetchone()

    print("BusinessMember:", member_res)

    if not member_res:
        print("ERROR: No BusinessMember record found!")
        exit(1)

    biz_id = member_res[1]

    biz_res = conn.execute(
        text("SELECT id, name FROM businesses WHERE id = :id"),
        {"id": biz_id},
    ).fetchone()

    print("Business:", biz_res)

print("\n✅ Phase 1 verification completed successfully.")