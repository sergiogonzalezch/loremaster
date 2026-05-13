#!/usr/bin/env python
"""Script para promover un usuario a administrador.

Uso:
    python scripts/make_admin.py <username>

Conecta directamente a la base de datos configurada en DATABASE_URL
y actualiza el campo is_admin del usuario indicado.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, select

from app.database import engine
from app.models.db.user import User


def main():
    """Busca un usuario por nombre de usuario y lo promueve a administrador."""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <username> [--force]")
        print("  --force: Omite la confirmación de seguridad (usar con precaución)")
        sys.exit(1)

    username = sys.argv[1]
    force = "--force" in sys.argv

    if not force:
        response = input(
            f"WARNING: You are about to make '{username}' an admin. "
            "This grants full system access. Continue? (yes/no): ",
        )
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username, not User.is_deleted),
        ).first()

        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)

        user.is_admin = True
        session.add(user)
        session.commit()

        print(f"User '{username}' is now an admin.")
        print(
            f"audit action=make_admin username={username} promoted_by={os.environ.get('USER', 'unknown')}",
        )


if __name__ == "__main__":
    main()
