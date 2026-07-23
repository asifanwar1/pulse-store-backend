"""One-off CLI to promote/create an admin account directly against the database.

Public registration and PATCH /users/me can no longer set user_type=ADMIN (that was a
privilege-escalation bug), so this is the only way to create the first admin. Run it
from the project root with the venv active:

    python -m scripts.create_admin --email you@example.com --password "Str0ng!Pass" --name "Your Name"

If the email already exists, it is promoted to ADMIN (and activated/verified) instead of
creating a duplicate account.
"""
import argparse
import sys

from app.core.security import hash_password
from app.database import SessionLocal
from app.features.users.models import User, UserStatus, UserType


def create_or_promote_admin(email: str, password: str | None, full_name: str | None) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.user_type = UserType.ADMIN.value
            user.is_active = True
            user.is_verified = True
            user.status = UserStatus.ACTIVE.value
            if password:
                user.hashed_password = hash_password(password)
            db.commit()
            print(f"Promoted existing user {email} to ADMIN.")
            return

        if not password or not full_name:
            print("No existing user with that email; --password and --name are required to create one.", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=email,
            full_name=full_name,
            address={},
            user_type=UserType.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        print(f"Created new ADMIN user {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Required when creating a new user")
    parser.add_argument("--name", dest="full_name", help="Required when creating a new user")
    args = parser.parse_args()
    create_or_promote_admin(args.email, args.password, args.full_name)
