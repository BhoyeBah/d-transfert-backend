import asyncio
import sys
import uuid
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password

async def main() -> None:
    print("Seed: Initialisation de l'administrateur de la plateforme...")
    try:
        async with AsyncSessionLocal() as session:
            # Vérifier si l'utilisateur existe déjà
            result = await session.execute(
                text("SELECT id FROM users WHERE matricule = :matricule"),
                {"matricule": "ADMIN"}
            )
            existing = result.fetchone()
            if existing:
                # Ne jamais réécrire le mot de passe d'un compte existant : ce script n'est
                # qu'un filet de sécurité pour recréer le compte s'il a disparu (ex. après une
                # restauration de sauvegarde), pas un reset périodique qui annulerait un
                # changement de mot de passe fait depuis l'interface d'administration.
                print("L'administrateur existe déjà, rien à faire.")
                return

            # Créer l'administrateur
            user_id = uuid.uuid4()
            pwd_hash = hash_password(get_settings().super_admin_initial_password)

            await session.execute(
                text("""
                    INSERT INTO users (
                        id, company_id, role_id, matricule, full_name, phone,
                        password_hash, is_owner, is_super_admin, is_active,
                        failed_login_attempts, created_at, updated_at
                    ) VALUES (
                        :id, NULL, NULL, :matricule, 'Super Admin', '+224600000000',
                        :password_hash, FALSE, TRUE, TRUE, 0, NOW(), NOW()
                    )
                """),
                {
                    "id": user_id,
                    "matricule": "ADMIN",
                    "password_hash": pwd_hash
                }
            )

            await session.commit()
            print("Administrateur de la plateforme créé avec succès (ADMIN).")
    except Exception as e:
        print(f"Erreur lors de la création de l'administrateur: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
