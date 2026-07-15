import asyncio
import sys
import uuid
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password

async def main() -> None:
    print("Seed: Initialisation de l'administrateur de la plateforme...")
    try:
        async with AsyncSessionLocal() as session:
            # Vérifier si l'utilisateur existe déjà
            result = await session.execute(
                text("SELECT id FROM users WHERE matricule = :matricule"),
                {"matricule": "admin@dtransfert.com"}
            )
            existing = result.fetchone()
            if existing:
                print("L'administrateur existe déjà. Mise à jour du mot de passe...")
                await session.execute(
                    text("UPDATE users SET password_hash = :password_hash WHERE matricule = :matricule"),
                    {
                        "matricule": "admin@dtransfert.com",
                        "password_hash": hash_password("passer123")
                    }
                )
                await session.commit()
                print("Mot de passe mis à jour avec succès.")
                return

            # Créer l'administrateur
            user_id = uuid.uuid4()
            pwd_hash = hash_password("passer123")
            
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
                    "matricule": "admin@dtransfert.com",
                    "password_hash": pwd_hash
                }
            )
            await session.commit()
            print("Administrateur de la plateforme créé avec succès (admin@dtransfert.com).")
    except Exception as e:
        print(f"Erreur lors de la création de l'administrateur: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
