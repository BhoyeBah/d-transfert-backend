# État d'implémentation — D-Transfert

Document de suivi de conformité par rapport au cahier des charges (`TODO.md`).
Dernière mise à jour : rapports avancés (mensuel, transactions par période, soldes
collaborateurs, historique wallet, activité employé, fournisseurs, clients, frais,
opérations rejetées/annulées), opérations nationales multi-devises (échange réel
avec taux de conversion), dimension type d'opération sur les taux privés, validation
entreprise "en attente" à l'inscription, dashboard employé distinct et scopé.

Légende : `Conforme` = couvre l'essentiel du cahier des charges · `Partiel` =
existe mais incomplet sur un point précis · `Manquant` = pas d'implémentation
réelle.

## Conformité module par module

| Module | Statut | Détail |
|---|---|---|
| Authentification | Conforme | Inscription, connexion, refresh token, reset par OTP (code à 6 chiffres, expiration 10 min, usage unique), verrouillage après 5 échecs (15 min), `/me`. Inscription en attente de validation plateforme (`require_company_approval`) configurable par le Super Admin. |
| Gestion entreprise | Conforme | Profil, lookup public par matricule (champs limités), activation automatique par défaut ou mise en attente de validation Super Admin selon le paramètre plateforme. |
| Gestion employés | Conforme | Création, liste, activation/désactivation, permissions. |
| Rôles et permissions | Conforme | RBAC backend, filtrage des actions par permission, 11 permissions du cahier des charges + 4 supplémentaires. |
| Wallets | Conforme | Création, mise à jour (avec log d'audit), statut, historique des mouvements, solde initial, wallet inactif bloqué pour toute nouvelle opération. |
| Opérations nationales | Conforme | Dépôt/retrait/échange/rééquilibrage/ajustement. Équilibre strict par devise pour le cas mono-devise ; **échange réel entre deux devises différentes** désormais supporté (`exchange_rate` sur `NationalOperation`, validation cohérence montant source × taux = montant destination). Frontend : ligne 2 auto-remplie (sens + montant, ou montant converti via le taux si devises différentes). |
| Entrées | Conforme | Création multi-wallet, fusion (reliquat conservé), annulation, statuts. Actions directes "Transformer en envoi"/"Transformer en paiement" sur la liste et la fiche détail. |
| Envois internationaux | Conforme | Création (directe ou depuis une entrée), validation croisée, rejet, annulation par l'initiateur, preuve, historique complet. `reliquat_action` réellement appliqué (`unallocated`/`fee`/`client_credit`). Dette client réversée sur rejet et annulation (mouvement inverse tracé, historique conservé). |
| Paiements collaborateurs | Conforme | Même couverture que les envois : `reliquat_action` appliqué, dette client réversée sur rejet/annulation, paiement direct depuis wallet ou entrée. |
| Collaborations | Conforme | Demande par matricule, acceptation/rejet, proposition de taux avec double validation (le proposant ne peut pas s'auto-accepter), historique des taux, notification sur proposition de taux. |
| Taux privés | Conforme | Taux par collaboration/pays/devise **et type d'opération** (mode d'envoi, optionnel), non visibles des collaborateurs, historisés. Un taux scopé à un mode d'envoi précis est prioritaire sur un taux générique lors de la résolution du taux appliqué à un envoi. |
| Taux collaboratifs | Conforme | Proposition/acceptation/rejet, historisation, figement par transaction (non-rétroactivité vérifiée par tests). |
| Clients et dettes clients | Conforme | Création rapide, consultation, mouvements. Cycle de correction fermé : la dette (ou le crédit de reliquat) créée à l'initiation d'un envoi/paiement est annulée par un mouvement inverse si l'opération est rejetée ou annulée avant validation. |
| Fournisseurs | Conforme | Création, rééquilibrage (dette/paiement), mouvements, contrôle de devise. |
| Preuves | Conforme | Upload, liste, téléchargement, rattachement strict à une opération (contrainte SQL `exactly_one_operation`), statut de validation (`pending`/`validated`/`rejected`) synchronisé automatiquement avec l'approbation/le rejet/l'annulation de l'opération parente. |
| Notifications | Partiel | Notifications internes cohérentes avec les événements (demande/acceptation/rejet de collaboration, envoi/paiement en attente, rejeté, annulé, taux proposé). Email/SMS/WhatsApp non branchés — explicitement "hors MVP" dans le cahier des charges lui-même (§37.2), différé sur confirmation explicite. |
| Dashboard | Conforme | **Owner** : soldes wallets, soldes collaborateurs, compteurs du jour, alertes (wallet en négatif, opération en attente > 72h). **Employé** : vue distincte et scopée à sa propre activité (`GET /dashboard/me`) — ses entrées/envois/paiements du jour, ses transactions en attente, nombre de wallets auxquels il a accès selon ses permissions. |
| Rapports | Conforme (CSV) | Rapport journalier et mensuel, transactions par période, solde par collaborateur, historique d'un wallet, activité par employé, rapport fournisseurs, rapport clients, rapport des frais (reliquats conservés en frais), rapport des opérations rejetées/annulées — tous avec vue JSON + export CSV. **Écart assumé** : export PDF/Excel natif non implémenté (CSV s'ouvre nativement dans Excel, jugé suffisant pour le MVP ; PDF nécessiterait une dépendance de rendu supplémentaire non justifiée à ce stade). |
| Audit logs | Conforme | Connexion, création (entrée/envoi/paiement), validation, rejet, annulation, modification de taux (proposition/rejet), modification de wallet, création d'employé, changement de permission, intervention admin — tous couverts. |
| Administration plateforme | Conforme | Statistiques, entreprises, utilisateurs, abonnements, paramètres (dont `require_company_approval`), logs système, comptes Super Admin. |
| Frontend | Conforme (MVP web) | Tous les écrans du MVP présents et navigables (sidebar complet, y compris Notifications, Rapports enrichis, Dashboard employé). Pas d'application mobile native — hors MVP par choix explicite du cahier des charges et confirmé par le porteur de projet (PWA responsive recommandée, non développée ici). |

## Corrections et ajouts apportés dans cette passe finale

1. **Validation entreprise "en attente" à l'inscription** : `PlatformSetting.require_company_approval`
   (paramètre Super Admin) détermine si une nouvelle entreprise est active immédiatement
   ou en attente. Connexion bloquée tant qu'une entreprise en attente n'est pas activée
   par un Super Admin (réutilise l'infrastructure `set_company_status` déjà existante).
2. **Dimension type d'opération sur les taux privés** : `PrivateSendingRate.operation_type`
   (nullable, aligné sur `SendMode`). La résolution du taux appliqué à un envoi préfère
   désormais un taux scopé au mode d'envoi (`cash`, `wave`, ...) avant de retomber sur un
   taux générique, sans casser le comportement existant (les taux sans type restent
   valables pour tous les modes).
3. **Opérations nationales multi-devises** : `NationalOperation.exchange_rate` (nullable) +
   validation Pydantic étendue — un échange entre deux devises différentes exige un taux,
   vérifie que le montant converti est cohérent (source × taux ≈ destination), et
   l'historise. L'annulation d'un échange multi-devises mirror correctement le taux
   d'origine dans l'opération de reversal.
4. **Rapports avancés** : nouveau module `report_service.py` + 9 nouveaux types de
   rapport (mensuel, transactions par période, solde par collaborateur, historique
   wallet, activité employé, fournisseurs, clients, frais, opérations rejetées/annulées),
   chacun avec vue JSON et export CSV, gated par les permissions `report.view`/`report.export`
   déjà existantes. Frontend : page `/reports` entièrement reconstruite avec une section
   par type de rapport, filtre de période partagé, sélecteurs wallet/employé.
5. **Dashboard employé dédié** : nouvel endpoint `GET /api/v1/dashboard/me`, scopé à
   l'activité propre de l'employé (ses entrées/envois/paiements créés aujourd'hui, ses
   transactions en attente, nombre de wallets auxquels il a accès selon `wallet.manage`).
   Le dashboard Owner reste inchangé ; le frontend bascule automatiquement entre les deux
   vues selon `is_owner`.

## Tests ajoutés (passe finale)

- `test_private_rate_scoped_to_operation_type_takes_priority` (`test_transfers.py`)
- `test_exchange_between_different_currencies_with_rate`,
  `test_exchange_missing_rate_for_multi_currency_rejected`,
  `test_exchange_rate_inconsistent_with_amounts_rejected`,
  `test_cancel_exchange_reversal_mirrors_rate` (`test_national_operations.py`)
- `test_registration_pending_when_approval_required`,
  `test_registration_active_by_default` (`test_auth.py`)
- `test_monthly_report_counts_operations_in_month`,
  `test_transactions_report_includes_transfers_and_payments`,
  `test_collaborator_balances_report`, `test_wallet_history_report`,
  `test_employee_activity_report`, `test_fees_report_from_reliquat_fee_action`,
  `test_rejected_operations_report`, `test_employee_dashboard_scoped_to_own_activity`,
  `test_employee_dashboard_hides_wallets_without_permission`
  (`test_dashboard_and_reports.py`)

Suite complète : **170 tests passent**. `alembic upgrade head` : propre, sans dérive.
Build + lint + typecheck frontend : clean.

## Écarts restants (hors MVP ou différés délibérément, avec accord explicite)

- **Notifications email/SMS/WhatsApp** : explicitement listées "hors MVP" par le cahier
  des charges lui-même (§37.2). Différé sur confirmation explicite du porteur de projet.
- **Application mobile native** : hors MVP (§37.2), PWA responsive recommandée à la place
  — l'interface web actuelle est responsive mais n'est pas empaquetée en PWA installable.
  Différé sur confirmation explicite du porteur de projet.
- **Export PDF/Excel natif des rapports** : seul le CSV est proposé (ouvrable nativement
  dans Excel). Un rendu PDF ou un fichier `.xlsx` avec mise en forme dédiée nécessiterait
  une nouvelle dépendance (reportlab/openpyxl) non justifiée pour l'usage MVP actuel.
