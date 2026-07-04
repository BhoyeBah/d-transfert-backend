# D-Transfert — Frontend

Interface web du backend D-Transfert. Next.js (App Router, TypeScript), Tailwind CSS + shadcn/ui
(composants écrits à la main dans ce dépôt — voir « Composants UI » ci-dessous).

## Architecture d'authentification (Backend-for-Frontend)

Le frontend ne parle **jamais** directement au backend FastAPI depuis le navigateur. À la place :

* Les tokens JWT (`access_token`/`refresh_token`) sont stockés dans des cookies **httpOnly**
  (`dt_access_token`, `dt_refresh_token`), posés uniquement par des Server Actions
  (`src/actions/auth.ts`) — jamais accessibles au JavaScript client.
* Les Server Components et Server Actions lisent le cookie et appellent l'API FastAPI directement
  depuis le serveur Next.js (`src/lib/api.ts`), en attachant `Authorization: Bearer <token>`.
  L'URL du backend (`API_BASE_URL`) n'est donc jamais exposée au client.
* `src/proxy.ts` (le « Proxy », anciennement Middleware sous Next.js < 16) s'exécute avant chaque
  page : il rafraîchit silencieusement le token d'accès expiré via `/auth/refresh` si un refresh
  token valide existe, et redirige vers `/login` (ou `/dashboard`) selon l'état de la session.

Voir `src/lib/session.ts`, `src/lib/api.ts` et `src/proxy.ts` pour le détail.

## Installation locale

```bash
npm install
cp .env.example .env.local   # ajuster API_BASE_URL si le backend ne tourne pas sur :8000
npm run dev
```

Le backend FastAPI doit tourner en parallèle (voir le README à la racine du dépôt) :

```bash
cd .. && poetry run uvicorn app.main:app --port 8000
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `API_BASE_URL` | URL du backend FastAPI, joignable uniquement depuis le serveur Next.js (jamais depuis le navigateur). |

## Composants UI

Le CLI `shadcn` nécessite un accès réseau à `ui.shadcn.com`, indisponible dans certains
environnements sandboxés. Les composants (`src/components/ui/*`) ont donc été écrits directement
à la main en suivant la structure standard shadcn/ui (Radix UI + `class-variance-authority` +
Tailwind), avec `components.json` conservé pour rester compatible avec le CLI si l'accès réseau
est disponible ailleurs (`npx shadcn@latest add <composant>`).

## Structure

```
src/
  app/
    (auth)/        pages publiques : login, register, forgot/reset password
    (app)/         pages protégées (sidebar + topbar), une page par module métier
  actions/         Server Actions ('use server') — mutations + gestion des cookies
  components/
    ui/            primitives shadcn/ui écrites à la main
    layout/        sidebar, topbar, shell applicatif
  lib/
    api.ts         client HTTP serveur-only vers FastAPI
    session.ts     lecture/écriture des cookies httpOnly
    data/          fonctions de lecture par domaine (Server Components)
    validation/    schémas zod partagés avec les formulaires
  proxy.ts         rafraîchissement de session + redirections (protégé/public)
```

## Design system

Palette teal/neutre à dominante froide (confiance, lisibilité financière), polices Geist
Sans/Mono, mode sombre activable (bouton dans la barre supérieure, persistance `localStorage`).
Voir `src/app/globals.css` pour les tokens de couleur (variables CSS, thème clair/sombre).
