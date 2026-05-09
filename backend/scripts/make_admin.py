#!/usr/bin/env python
"""Make a user admin.

Usage: python scripts/make_admin.py <username>
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, select
from app.database import engine
from app.models.db.user import User


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <username>")
        sys.exit(1)

    username = sys.argv[1]

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username, User.is_deleted == False)
        ).first()

        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)

        user.is_admin = True
        session.add(user)
        session.commit()

        print(f"User '{username}' is now an admin.")


if __name__ == "__main__":
    main()
