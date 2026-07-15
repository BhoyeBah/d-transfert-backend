# Diagnostic de préparation à la production — D-Transfert

Date : 2026-07-14 (mise à jour après correctifs — diagnostic initial daté du 2026-07-13)
Basé sur : lecture complète du cahier des charges (`TODO.md`, 41 sections), lecture du
code backend (FastAPI) et frontend (Next.js 16), exécution réelle de la suite de tests
(218 tests après ajout des tests de non-régression sur les correctifs), du build de
production frontend, du typecheck et du lint.

**Verdict global : les 5 points bloquants identifiés lors du diagnostic initial ont
été corrigés et vérifiés (tests + exécution réelle).** Le projet reste par ailleurs
fonctionnellement conforme au MVP du cahier des charges. Ce qui reste (section 8) est
recommandé mais ne bloque plus un premier lancement contrôlé.

---

## 1. Conformité fonctionnelle vs cahier des charges

Le fichier `IMPLEMENTATION_STATUS.md` (déjà tenu à jour au fil du projet) recense un
module par module. Résumé :

| Statut | Modules |
|---|---|
| **Conforme** | Authentification, entreprises, employés, rôles/permissions, wallets, opérations nationales (mono et multi-devises), entrées, envois internationaux, paiements collaborateurs, collaborations, taux privés, taux collaboratifs, clients/dettes, fournisseurs, preuves, dashboard (Owner + Employé), rapports (JSON + CSV), audit logs, administration plateforme, frontend web MVP |
| **Partiel (assumé)** | Notifications — internes seulement ; email/SMS/WhatsApp explicitement "hors MVP" par le cahier des charges lui-même (§37.2) |
| **Écart assumé** | Export PDF/Excel natif des rapports (CSV seulement, ouvrable dans Excel) ; application mobile native (PWA recommandée à la place, non empaquetée) |

Ces trois écarts sont **explicitement listés comme hors-MVP par le cahier des charges
lui-même** (§37.2) — ce ne sont pas des bugs, mais des reports assumés.

### Points ouverts issus des échanges précédents (à vérifier avant mise en prod)

- **Sélecteur de devise à l'inscription** : un utilisateur a signalé un menu qui ne
  s'ouvrait pas sur `/register`. Non reproduit en test (Playwright confirme un
  fonctionnement correct côté code) — probablement un souci d'environnement/navigateur
  côté utilisateur, mais à reconfirmer avec lui avant de le classer sans suite.
- **Affichage des paires de devises sur les taux** (ex. `FCFA → GNF`) : proposition
  faite en cours de route, jamais tranchée ni implémentée. Amélioration UX facultative.

---

## 2. Sécurité

| Point | État | Détail |
|---|---|---|
| Hash des mots de passe | ✅ Bon | Argon2 (`passlib`), algorithme moderne recommandé. |
| JWT — secret par défaut | ✅ **Corrigé** | `app/core/config.py` refuse maintenant de démarrer (`RuntimeError`) si `ENVIRONMENT=production` et que `JWT_SECRET_KEY` vaut encore la valeur par défaut du dépôt. Testé (`app/tests/unit/test_config.py`). |
| Révocation de session | ✅ **Corrigé (mécanisme basique)** | Deux mécanismes ajoutés : (1) table `revoked_tokens` (jti + expiration) alimentée par un nouvel endpoint `POST /auth/logout`, qui révoque explicitement l'access token courant et le refresh token fourni ; (2) `users.password_changed_at` — tout token émis avant cette date est rejeté, donc un reset de mot de passe invalide **immédiatement toutes les sessions existantes** sans avoir à énumérer chaque token émis. Testé (`test_logout_revokes_access_and_refresh_tokens`, `test_password_reset_invalidates_previously_issued_tokens`). **Limite assumée** : la révocation par `jti` ne couvre que les déconnexions explicites (bouton "Se déconnecter") — un vol de token entre deux requêtes sans logout explicite reste valide jusqu'à expiration naturelle (30 min pour l'access token) sauf s'il y a un reset de mot de passe entre-temps. Pas de purge automatique des lignes `revoked_tokens` expirées (à ajouter si le volume devient significatif — la table ne grossit qu'au rythme des déconnexions explicites). |
| Verrouillage brute-force par compte | ✅ Bon | 5 échecs → verrouillage 15 min, par compte (inchangé). |
| Rate limiting HTTP | ✅ **Corrigé** | `slowapi`, en mémoire par processus, appliqué sur `/auth/register` (5/min), `/auth/login` (10/min), `/auth/forgot-password` (5/min), `/auth/reset-password` (10/min), clé = adresse IP. Testé (`test_register_is_rate_limited_per_ip`). **Limite à connaître** : keyé par IP source vue par FastAPI — si le déploiement passe derrière un reverse-proxy sans transmission correcte de l'IP réelle du client (`X-Forwarded-For`), tous les utilisateurs partageraient la même IP apparente (celle du proxy) et pourraient se bloquer mutuellement. Le `Caddyfile` fourni (section 3) transmet correctement l'IP cliente par défaut ; à vérifier si un autre reverse-proxy est utilisé. En mémoire par processus : si le backend passe un jour en plusieurs instances, migrer vers un stockage partagé (`storage_uri="redis://..."`, supporté nativement par slowapi). |
| CORS | ➖ Non configuré, non nécessaire (confirmé) | Le frontend appelle le backend uniquement côté serveur (`serverFetch`, `proxy.ts`) — aucun appel client-side direct vérifié dans le code. Pas de CORS à ajouter tant que ce pattern BFF est respecté. |
| Cookies de session | ✅ Bon | `httpOnly: true`, `secure` activé en production, `sameSite: lax` (inchangé). |
| Fuite d'erreurs | ✅ Bon | Les exceptions non gérées sont loggées en base (`system_logs`) et renvoient un message générique au client, jamais de stack trace (inchangé). |
| Isolation multi-entreprise | ✅ Bon | Toutes les requêtes scopent par `company_id` dérivé du token ; testé (401/403/404 selon les cas) (inchangé). |
| En-têtes de sécurité HTTP | ✅ **Corrigé** | Backend (middleware FastAPI) et frontend (`next.config.ts` → `headers()`) envoient tous deux `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` ; `Strict-Transport-Security` ajouté uniquement quand `ENVIRONMENT`/`NODE_ENV=production` (pour ne pas piéger un accès HTTP local). `Permissions-Policy` restrictive côté frontend. CSP non ajoutée (nécessiterait d'auditer tous les scripts/inline styles du frontend — à faire dans un second temps si besoin). |

---

## 3. Infrastructure & déploiement

| Point | État | Détail |
|---|---|---|
| Dockerfile backend | ✅ Correct | Inchangé — migration automatique au démarrage, `PORT` configurable. |
| Dockerfile frontend | ✅ Correct | Inchangé — build multi-stage, sortie `standalone`. |
| `docker-compose.yml` (dev) | ➖ Toujours dev seulement, par design | Reste tel quel pour le développement local (Postgres seul) — un fichier dédié à la production a été ajouté à côté (voir ligne suivante), pas de raison de fusionner les deux usages. |
| `docker-compose.prod.yml` | ✅ **Ajouté** | Stack complète : `postgres` (volume nommé, healthcheck), `backend` (volume nommé pour `uploads/`, variables requises via `${VAR:?message}` — refuse de démarrer sans secrets explicitement fournis), `frontend`, `reverse-proxy` (Caddy — HTTPS/Let's Encrypt automatique via `DOMAIN`, en-têtes transmis). Validé avec `docker compose -f docker-compose.prod.yml config` (voir `.env.prod.example` pour les variables à fournir). |
| Persistance des preuves (`uploads/`) | ✅ **Corrigé** | Volume Docker nommé (`dtransfert_uploads`) déclaré dans `docker-compose.prod.yml` — un redéploiement ne perd plus les fichiers. Le stockage reste local au disque du serveur (choix assumé par le cahier des charges §36.2, migration S3 recommandée plus tard si le volume le justifie, cf. section 8). |
| CI/CD | ✅ **Ajouté** | `.github/workflows/ci.yml` : job backend (Postgres de service, `alembic upgrade head` + `alembic check` + `alembic downgrade base` pour détecter toute dérive modèles/migrations, puis suite de tests complète) ; job frontend (`npm run lint`, `tsc --noEmit`, `next build`). Se déclenche sur push vers `main` et sur toute pull request. |
| Sauvegardes base de données | ✅ Partiel | Des scripts d'exploitation `scripts/db_backup.sh` et `scripts/db_restore.sh` sont fournis, et une interface admin permet désormais de créer/lister/restaurer les backups. Le système fait des dumps `pg_dump -Fc` compressés et restaure via `pg_restore --clean --if-exists`. Il reste à **planifier l'exécution automatique** (cron/systemd timer/outil d'hébergement) et à tester une restauration sur l'infra cible avant le premier vrai lancement. |
| Variables d'environnement | ✅ Bien documentées, désormais validées | `.env.example` (dev) et `.env.prod.example` (prod, nouveau) complets ; `JWT_SECRET_KEY` par défaut désormais bloqué en production (voir section 2). |

---

## 4. Fiabilité & qualité du code

| Vérification | Résultat |
|---|---|
| Suite de tests backend | **218 / 218 passent** (212 initiaux + 6 nouveaux tests couvrant les correctifs : révocation de session ×2, garde-fou JWT ×3, rate limiting ×1), exécution réelle contre une vraie base Postgres, aucun mock DB |
| `alembic upgrade head` / `alembic check` | Propre, aucune dérive entre modèles et migrations (deux nouvelles migrations ajoutées : `settles_debt` sur `payments`, `password_changed_at` + `revoked_tokens`) |
| Typecheck frontend (`tsc --noEmit`) | Propre, 0 erreur |
| Lint frontend (`eslint`) | Propre, 0 erreur |
| Build de production frontend (`next build`) | Réussi, 29 routes générées sans erreur |

---

## 5. Observabilité

| Point | État |
|---|---|
| Logs applicatifs structurés | ⚠️ Partiel (inchangé) — table `system_logs` en base, pas d'export vers un agrégateur externe |
| Suivi d'erreurs (Sentry ou équivalent) | ❌ Absent (inchangé) — nécessite un choix de compte/service externe, hors périmètre de ce qui est décidable en code seul |
| Alerting (erreurs 500 en rafale, base injoignable, etc.) | ❌ Absent (inchangé) |
| Métriques (latence, taux d'erreur, charge) | ❌ Absent (inchangé) |

Non bloquant pour un premier lancement contrôlé avec supervision manuelle des
`system_logs`, mais recommandé avant une montée en charge réelle (section 8).

---

## 6. Performance & scalabilité

- Pas de Redis ni de cache — non bloquant à l'échelle actuelle. Le rate limiting
  ajouté (section 2) est en mémoire par processus ; s'il faut un jour plusieurs
  instances backend, il faudra un stockage partagé (Redis) à la fois pour le rate
  limiting et pour le cache éventuel.
- Le stockage de fichiers sur disque local (volume Docker désormais persistant, mais
  toujours local à une seule machine) reste un frein au scaling horizontal du backend
  tant qu'il n'est pas migré vers un stockage partagé (S3-compatible).
- Aucun test de charge n'a été effectué — les 218 tests couvrent la correction
  fonctionnelle, pas le comportement sous charge.

---

## 7. Statut des points bloquants du diagnostic initial

| # | Point | Statut |
|---|---|---|
| 1 | Secret JWT fort et unique en production | ⚠️ Reste une action de déploiement (générer la valeur réelle) — le garde-fou technique qui l'impose est en place |
| 2 | Garde-fou au démarrage contre le secret par défaut | ✅ Corrigé |
| 3 | Volume persistant pour `uploads/` | ✅ Corrigé (`docker-compose.prod.yml`) |
| 4 | Sauvegarde automatique Postgres | ❌ Reste à faire — dépend de l'infra d'hébergement choisie |
| 5 | `docker-compose.prod.yml` complet | ✅ Corrigé |

Le point 1 n'est pas "corrigeable en code" par nature : c'est une valeur secrète à
générer et injecter au moment du déploiement (`openssl rand -hex 32`, documenté dans
`.env.prod.example`) — mais le système refuse maintenant de démarrer sans elle en
production, donc l'oubli n'est plus silencieux.

Le point 4 reste hors périmètre de ce qui est faisable en modifiant le dépôt : c'est
une décision et une configuration d'infrastructure (quel hébergeur, quelle politique
de rétention), pas une fonctionnalité applicative.

## 8. Fortement recommandé, non bloquant pour un premier lancement contrôlé

- Ajouter un service d'alerting minimal sur les erreurs serveur (Sentry gratuit ou
  équivalent auto-hébergé) — la table `system_logs` existe déjà, il "suffit" de la
  brancher ou d'ajouter un hook d'envoi.
- Planifier la migration du stockage des preuves vers un stockage S3-compatible dès
  que le volume d'usage le justifie (déjà anticipé et budgété par le cahier des
  charges lui-même).
- Étendre la révocation de session : purge périodique des lignes `revoked_tokens`
  expirées si le volume de déconnexions devient significatif (actuellement sans
  impact mesurable).
- Si le déploiement passe un jour à plusieurs instances backend : migrer le rate
  limiting et un éventuel cache vers Redis (stockage partagé).
- Planifier la sauvegarde Postgres automatique via `cron` ou `systemd timer` sur
  l'hôte Hetzner, puis tester une restauration complète au moins une fois.

## 9. Ce qui n'a pas besoin d'être traité avant la mise en ligne

- Les écarts fonctionnels listés en section 1 (notifications email/SMS, export
  PDF/Excel natif, application mobile native) sont **explicitement hors MVP par le
  cahier des charges**, pas des manques à corriger dans l'urgence.
- Redis / cache : non nécessaire au volume actuel.
- CSP (Content-Security-Policy) : les autres en-têtes de sécurité sont en place ;
  la CSP demande un audit préalable des scripts/styles inline du frontend pour éviter
  de casser l'application, à traiter séparément plutôt que dans l'urgence.

---

## Conclusion

Les 5 points bloquants identifiés le 2026-07-13 ont été traités : garde-fou JWT au
démarrage, révocation de session (logout + invalidation sur reset de mot de passe),
rate limiting sur les endpoints d'authentification, en-têtes de sécurité HTTP,
`docker-compose.prod.yml` complet avec volume persistant pour les preuves, et pipeline
CI. Tout est testé (218 tests, dont 6 nouveaux ciblant spécifiquement ces correctifs)
et vérifié par exécution réelle (suite de tests, `alembic check`, build de production,
lint, typecheck, et validation du compose de production).

**Ce qui reste** (section 8) ne bloque plus un premier lancement contrôlé : sauvegarde
Postgres (décision d'infrastructure), alerting externe (Sentry ou équivalent, décision
de compte/service), et migration du stockage des preuves vers S3 (à planifier selon le
volume réel d'usage, déjà anticipé par le cahier des charges lui-même).
