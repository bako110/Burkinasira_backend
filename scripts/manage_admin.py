"""Gestion du compte administrateur.

Ce script :
  1. supprime tous les comptes ayant le rôle "admin" dans la base ;
  2. crée un unique compte admin `admin@burkinasira.com`.

Le mot de passe n'est jamais écrit en dur : il est lu depuis l'argument
`--password` ou la variable d'environnement `ADMIN_PASSWORD`.

Usage (depuis backend/, venv activé) :

    python -m scripts.manage_admin --password "MotDePasseFort!"

ou

    ADMIN_PASSWORD="MotDePasseFort!" python -m scripts.manage_admin

Options :
    --email        Adresse de l'admin à créer (défaut: admin@burkinasira.com)
    --name         Nom affiché (défaut: Administrateur FasoViva)
    --keep-others  Ne supprime pas les autres admins, met seulement à jour / crée celui-ci
    --dry-run      Affiche ce qui serait fait, sans rien modifier
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

# Permet `python scripts/manage_admin.py` autant que `python -m scripts.manage_admin`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import UserRole, UserStatus  # noqa: E402

COLLECTION = "users"
DEFAULT_EMAIL = "admin@burkinasira.com"
DEFAULT_NAME = "Administrateur BurkinaSira"


async def run(email: str, name: str, password: str, keep_others: bool, dry_run: bool) -> None:
    await connect_to_mongo()
    db = get_database()
    users = db[COLLECTION]

    email = email.strip().lower()

    # 1. Lister les admins existants
    existing_admins = await users.find({"role": UserRole.ADMIN.value}).to_list(length=1000)
    print(f"Admins actuels en base : {len(existing_admins)}")
    for a in existing_admins:
        print(f"  - {a.get('email')}  (id={a['_id']}, status={a.get('status')})")

    if dry_run:
        if keep_others:
            print(f"\n[dry-run] Mettrait à jour / créerait uniquement : {email}")
        else:
            to_delete = [a for a in existing_admins if a.get("email") != email]
            print(f"\n[dry-run] Supprimerait {len(to_delete)} admin(s) : "
                  + ", ".join(a.get("email", "?") for a in to_delete))
            print(f"[dry-run] Créerait / mettrait à jour : {email}")
        await close_mongo_connection()
        return

    # 2. Supprimer les autres admins (sauf si --keep-others)
    if not keep_others:
        res = await users.delete_many({"role": UserRole.ADMIN.value, "email": {"$ne": email}})
        print(f"\nAdmins supprimés : {res.deleted_count}")

    # 3. Créer ou mettre à jour l'admin cible
    now = datetime.utcnow()
    hashed = hash_password(password)

    existing = await users.find_one({"email": email})
    if existing:
        await users.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "full_name": name,
                "hashed_password": hashed,
                "role": UserRole.ADMIN.value,
                "status": UserStatus.ACTIVE.value,
                "is_verified": True,
                "updated_at": now,
            }},
        )
        print(f"Admin mis à jour : {email} (id={existing['_id']})")
    else:
        doc = {
            "full_name": name,
            "email": email,
            "phone": None,
            "hashed_password": hashed,
            "role": UserRole.ADMIN.value,
            "status": UserStatus.ACTIVE.value,
            "is_verified": True,
            "avatar_url": None,
            "preferred_language": "fr",
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        res = await users.insert_one(doc)
        print(f"Admin créé : {email} (id={res.inserted_id})")

    # 4. Contrôle final
    final_admins = await users.find({"role": UserRole.ADMIN.value}).to_list(length=1000)
    print(f"\nAdmins en base après opération : {len(final_admins)}")
    for a in final_admins:
        print(f"  - {a.get('email')}  (status={a.get('status')}, verified={a.get('is_verified')})")

    await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Réinitialise le compte administrateur.")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    parser.add_argument("--keep-others", action="store_true",
                        help="Ne pas supprimer les autres comptes admin")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.password:
        parser.error("Mot de passe requis : --password ... ou variable ADMIN_PASSWORD")
    if args.password and len(args.password) < 10:
        parser.error("Mot de passe trop court (10 caractères minimum).")

    asyncio.run(run(
        email=args.email,
        name=args.name,
        password=args.password or "",
        keep_others=args.keep_others,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
