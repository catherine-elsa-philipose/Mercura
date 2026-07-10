import os
import secrets

def setup_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    
    secret_exists = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "SECRET_KEY=" in content:
                secret_exists = True

    if not secret_exists:
        new_secret = secrets.token_urlsafe(32)
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nSECRET_KEY={new_secret}\n")
        print("SECRET_KEY generated and appended to .env safely.")
    else:
        print("SECRET_KEY already exists in .env.")

if __name__ == "__main__":
    setup_env()
