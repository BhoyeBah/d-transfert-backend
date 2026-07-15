# D-Transfert — API Backend

API backend de D-Transfert : gestion multi-entreprises des wallets, opérations nationales
(dépôt/retrait/échange/rééquilibrage sans frais), collaborations inter-entreprises avec taux
collaboratifs et privés, envois internationaux, paiements collaborateurs, entrées et leur
fusion/transformation, clients et fournisseurs avec suivi de dettes, dashboard, rapports,
notifications et audit logs.

Stack : FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL + Pydantic v2 + JWT (accès/refresh)
+ Argon2 + RBAC par permissions.

## Prérequis

* Python 3.11+
* PostgreSQL 16 (ou `docker-compose.yml` fourni)
* [Poetry](https://python-poetry.org/) ou `pip` (le projet est un paquet `pyproject.toml` standard)

## Installation locale

```bash
git clone <url-du-repo>
cd d-transfert
poetry install --with dev
# ou : pip install -e ".[dev]"
```

## Base de données PostgreSQL

Un `docker-compose.yml` fournit une instance PostgreSQL prête à l'emploi pour le développement :

```bash
docker compose up -d
```

Cela démarre PostgreSQL sur `localhost:55432` (voir le mapping de port dans
`docker-compose.yml`) avec l'utilisateur/mot de passe/base `dtransfert`/`dtransfert`/`dtransfert`.
Le port 55432 (plutôt que le 5432 standard) évite un conflit si un PostgreSQL natif tourne déjà
sur la machine — dans ce cas, adaptez `DATABASE_URL` dans `.env` en conséquence (le défaut du
paquet pointe vers `localhost:5432`, pas vers l'instance Docker).

Pour les tests, une base **séparée** est utilisée (`dtransfert_test`, voir
`app/tests/conftest.py`) afin de ne jamais toucher aux données de développement. Créez-la une
fois :

```bash
psql "postgresql://dtransfert:dtransfert@localhost:55432/postgres" -c "CREATE DATABASE dtransfert_test;"
```

## Variables d'environnement

Copiez `.env.example` vers `.env` et ajustez si besoin :

| Variable | Description | Exemple |
|---|---|---|
| `ENVIRONMENT` | Environnement d'exécution (`development`/`production`) | `development` |
| `DATABASE_URL` | URL de connexion PostgreSQL asyncpg (base de développement/production, **pas** la base de test) | `postgresql+asyncpg://dtransfert:dtransfert@localhost:5432/dtransfert` |
| `JWT_SECRET_KEY` | Clé de signature des JWT — **à changer impérativement en production** (32 octets minimum) | `dev-only-change-me-32-bytes-minimum-secret-key` |
| `JWT_ALGORITHM` | Algorithme de signature JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token d'accès | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Durée de vie du token de rafraîchissement | `14` |

```bash
cp .env.example .env
```

## Migrations Alembic

Les migrations créent le schéma complet (29 tables), seedent les 15 permissions et les 3 rôles
par défaut (`owner`, `employee`, `super_admin`). Les seeds sont des constantes littérales dans
chaque migration (pas d'import du code vivant), afin qu'une base vierge rejouée aujourd'hui ou
dans un an obtienne exactement le même résultat historique.

```bash
# Appliquer toutes les migrations sur une base vierge
poetry run alembic upgrade head

# Vérifier qu'il n'y a aucun drift entre les modèles et les migrations
poetry run alembic check

# Revenir à une base vide (utile pour retester une installation from scratch)
poetry run alembic downgrade base

# Créer une nouvelle migration après modification des modèles
poetry run alembic revision --autogenerate -m "description"
```

## Lancer l'API

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

* Swagger UI : http://localhost:8000/docs
* ReDoc : http://localhost:8000/redoc
* OpenAPI JSON : http://localhost:8000/openapi.json
* Health check : http://localhost:8000/health

Toutes les routes métier sont préfixées par `/api/v1`. L'authentification se fait via
`Authorization: Bearer <access_token>`, obtenu via `POST /api/v1/auth/login` (matricule
d'entreprise pour l'Owner, matricule + téléphone pour un employé).

## Comptes de test

Chaque entreprise se crée elle-même via `POST /api/v1/auth/register` (voir `/docs` pour le payload
exact), ce qui crée automatiquement son compte Owner.

Il n'y a pas de compte Super Admin pré-seedé. Une fois qu'un premier compte Super Admin existe, il
peut en créer d'autres via `/admin/platform-admins` (frontend) ou `POST /api/v1/admin/platform-admins`
(API). Pour créer ce tout premier compte, insérez-le directement en base — voir
`app/tests/integration/test_admin.py::_create_super_admin` pour un exemple des champs requis
(`company_id` nul, `is_super_admin=True`, mot de passe hashé avec `app.core.security.hash_password`).

## Données fictives

Pour peupler une base de développement avec des données de test réalistes, lancez le script de seed :

```bash
python scripts/seed_demo.py
```

Pour cibler une entreprise existante, passez son matricule :

```bash
python scripts/seed_demo.py --company-code DT-VSVBELC5
```

Sans option, le script crée un tenant principal de démonstration et 15 entreprises partenaires.
Avec `--company-code`, il peuple l'entreprise existante indiquée. Dans les deux cas, il génère au
moins 15 enregistrements pour les modules métier principaux : employés, wallets, collaborations,
entrées, transferts, paiements, fournisseurs, opérations nationales et preuves. Les notifications
et les audit logs sont générés automatiquement par les services métier.

## Tests

```bash
# Suite complète (contre la base dtransfert_test réelle, aucun mock de DB)
poetry run pytest -q

# Un seul fichier
poetry run pytest -q app/tests/integration/test_transfers.py
```

Les tests d'intégration tournent contre un vrai PostgreSQL et s'exécutent chacun dans une
transaction annulée en fin de test (isolation par SAVEPOINT), donc aucune donnée ne persiste
entre deux tests.

## Structure du projet

```
app/
  core/        configuration, sécurité (JWT/Argon2), permissions RBAC, gestion des erreurs
  models/      modèles SQLAlchemy (29 tables)
  repositories/ accès DB par entité, toujours scopé par company_id
  services/    logique métier et règles d'intégrité financière
  schemas/     schémas Pydantic (requêtes/réponses)
  routers/     endpoints FastAPI, un fichier par domaine métier
  tests/       tests d'intégration (via HTTP réel) et unitaires
alembic/       migrations, une par phase fonctionnelle
```

## Déploiement en production

`docker-compose.prod.yml` fournit une stack complète (Postgres, backend, frontend,
reverse-proxy Caddy avec HTTPS automatique) :

```bash
cp .env.prod.example .env.prod   # remplir les valeurs, voir les commentaires du fichier
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Le fichier refuse de démarrer sans que `POSTGRES_PASSWORD` et `JWT_SECRET_KEY` soient
explicitement définis (jamais de valeur par défaut en clair pour ces secrets). Voir
`PRODUCTION_READINESS.md` pour le diagnostic complet de préparation à la production
(sécurité, infrastructure, observabilité) et ce qui reste à traiter au niveau
infrastructure (sauvegardes Postgres, alerting externe).

## Sauvegarde et restauration

Deux scripts d'exploitation et une interface admin sont fournis pour les sauvegardes
PostgreSQL sur un hébergement comme Hetzner :

```bash
# Créer une sauvegarde compressée dans ./backups
bash scripts/db_backup.sh

# Restaurer une sauvegarde existante
RESTORE_FORCE=1 bash scripts/db_restore.sh ./backups/dtransfert_20260715_153000.dump.gz
```

Dans l'interface d'administration, va dans **Paramètres plateforme** :

* bouton **Créer une sauvegarde**
* liste des backups disponibles
* bouton **Restaurer** avec confirmation

Par défaut, le script de backup :

* lit `.env.prod`
* prend un dump `pg_dump -Fc`
* compresse le résultat en `.dump.gz`
* conserve les `14` sauvegardes les plus récentes dans `backups/`

La restauration utilise `pg_restore --clean --if-exists` et doit être lancée pendant
une fenêtre de maintenance, avec les écritures applicatives arrêtées.

Pour l'automatiser sur Hetzner, ajoute simplement un `cron` ou un `systemd timer` qui
exécute `bash scripts/db_backup.sh` chaque nuit, par exemple :

```cron
0 2 * * * cd /opt/d-transfert && BACKUP_DIR=/var/backups/dtransfert bash scripts/db_backup.sh >> /var/log/dtransfert-backup.log 2>&1
```
