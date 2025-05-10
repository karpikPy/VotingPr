import sys
import os
from VotingProject1.backend.database.database import SessionLocal
from VotingProject1.backend.API.models import User


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def set_user_as_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_admin = True
            db.commit()
            print(f"Користувач з email '{email}' тепер адміністратор.")
        else:
            print(f"Користувача з email '{email}' не знайдено.")
    except Exception as e:
        db.rollback()
        print(f"Виникла помилка: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Використання: python backend/admin_utils.py <email_користувача>")
        sys.exit(1)

    user_email = sys.argv[1]
    set_user_as_admin(user_email)
