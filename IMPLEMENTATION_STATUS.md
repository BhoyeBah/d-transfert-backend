# État d'implémentation — D-Transfert

Document de suivi de conformité par rapport au cahier des charges (`TODO.md`).
Dernière mise à jour : correctifs sur la dette client (rejet/annulation), la
devise du formulaire d'envoi, le statut de validation des preuves, et les
notifications (annulation, proposition de taux).

Légende : `Conforme` = couvre l'essentiel du cahier des charges · `Partiel` =
existe mais incomplet sur un point précis · `Manquant` = pas d'implémentation
réelle.

## Conformité module par module

| Module | Statut | Détail |
|---|---|---|
| Authentification | Conforme | Inscription, connexion, refresh token, reset par OTP (code à 6 chiffres, expiration 10 min, usage unique), verrouillage après 5 échecs (15 min), `/me`. |
| Gestion entreprise | Conforme | Profil, lookup public par matricule (champs limités), toujours créée active (pas de mode "en attente de validation" — écart mineur, non bloquant pour le MVP). |
| Gestion employés | Conforme | Création, liste, activation/désactivation, permissions. |
| Rôles et permissions | Conforme | RBAC backend, filtrage des actions par permission, 11 permissions du cahier des charges + 4 supplémentaires. |
| Wallets | Conforme | Création, mise à jour (avec log d'audit), statut, historique des mouvements, solde initial, wallet inactif bloqué pour toute nouvelle opération. |
| Opérations nationales | Partiel | Dépôt/retrait/échange/rééquilibrage/ajustement + équilibre strict par devise. **Frontend** : ligne 2 auto-remplie (sens + montant) depuis la ligne 1 sur le cas simple à 2 lignes. **Écart connu** : pas de taux de conversion pour un échange multi-devises (le modèle `NationalOperationLine` n'a pas de champ taux/montant converti) — nécessiterait une migration, non traité dans cette passe. |
| Entrées | Conforme | Création multi-wallet, fusion (reliquat conservé), annulation, statuts. Actions directes "Transformer en envoi"/"Transformer en paiement" sur la liste et la fiche détail. |
| Envois internationaux | Conforme | Création (directe ou depuis une entrée), validation croisée, rejet, annulation par l'initiateur, preuve, historique complet. **`reliquat_action` réellement appliqué** (`unallocated`/`fee`/`client_credit`) dans `transfer_service.create_transfer`. **Dette client désormais réversée** sur rejet et annulation (mouvement inverse tracé, historique conservé). Case à cocher explicite "Un client doit ce montant" côté frontend. |
| Paiements collaborateurs | Conforme | Même couverture que les envois : `reliquat_action` appliqué, dette client réversée sur rejet/annulation, paiement direct depuis wallet ou entrée. |
| Collaborations | Conforme | Demande par matricule, acceptation/rejet, proposition de taux avec double validation (le proposant ne peut pas s'auto-accepter), historique des taux. **Notification ajoutée** sur proposition de taux (absente auparavant). |
| Taux privés | Partiel | Taux par collaboration/pays/devise, non visibles des collaborateurs, historisés. Pas de dimension "type d'opération" distincte (le cahier des charges la mentionne comme optionnelle — `"si nécessaire"`) : jugé non bloquant. |
| Taux collaboratifs | Conforme | Proposition/acceptation/rejet, historisation, figement par transaction (non-rétroactivité vérifiée par tests). |
| Clients et dettes clients | Conforme | Création rapide, consultation, mouvements. **Cycle de correction fermé** : la dette (ou le crédit de reliquat) créée à l'initiation d'un envoi/paiement est maintenant annulée par un mouvement inverse si l'opération est rejetée ou annulée avant validation. |
| Fournisseurs | Conforme | Création, rééquilibrage (dette/paiement), mouvements, contrôle de devise. Libellés clarifiés côté frontend (effet sur le wallet explicite). |
| Preuves | Conforme | Upload, liste, téléchargement, rattachement strict à une opération (contrainte SQL `exactly_one_operation`). **Statut de validation ajouté** (`pending`/`validated`/`rejected`), synchronisé automatiquement avec l'approbation/le rejet/l'annulation de l'envoi ou du paiement parent. |
| Notifications | Partiel | Notifications internes cohérentes avec les événements (demande/acceptation/rejet de collaboration, envoi/paiement en attente, rejeté, **annulé**, **taux proposé**). Email/SMS/WhatsApp non branchés — explicitement "hors MVP" dans le cahier des charges lui-même (§37.2). |
| Dashboard | Partiel | Soldes wallets, soldes collaborateurs, compteurs du jour, alertes (wallet en négatif, opération en attente > 72h). Pas de vue distincte pour l'employé (même schéma que l'Owner, filtré par permissions au niveau routeur). |
| Rapports | Partiel | Rapport journalier + export CSV + journal d'audit intégré. **Écart assumé** : pas de rapport mensuel, ni export PDF/Excel, ni rapports séparés par collaborateur/wallet/employé/fournisseur/client. Non traité dans cette passe (chantier disctinct, cf. section suivante). |
| Audit logs | Conforme | Connexion, création (entrée/envoi/paiement), validation, rejet, annulation, modification de taux (proposition/rejet), modification de wallet, création d'employé, changement de permission, intervention admin — tous couverts. |
| Administration plateforme | Conforme | Statistiques, entreprises, utilisateurs, abonnements, paramètres, logs système, comptes Super Admin. |
| Frontend | Conforme (MVP web) | Tous les écrans du MVP présents et navigables (sidebar complet, y compris Notifications). Pas d'application mobile native — hors MVP par choix explicite du cahier des charges (PWA responsive recommandée, non développée ici). |

## Corrections apportées dans cette passe

1. **Dette client non réversée sur rejet/annulation** (bug réel, confirmé par lecture de code) :
   `client_service.reverse_movements_for_source` — annule l'effet net déjà appliqué au
   client pour une opération donnée (dette initiale ou crédit de reliquat), via un
   mouvement inverse tracé (pas de suppression d'historique). Branché dans
   `transfer_service.reject_transfer/cancel_transfer` et l'équivalent paiement.
   Bug additionnel trouvé et corrigé en cours de route : une édition précédente avait
   accidentellement supprimé la fonction `client_service.get_client`.
2. **`reliquat_action` non appliqué** : vérifié FAUX pour ce dépôt — la logique était déjà
   implémentée et testée (`unallocated`/`fee`/`client_credit`) dans une passe précédente
   de cette même session. Confirmé par les tests `test_create_transfer_reliquat_*`.
3. **Devise obsolète/vide dans le formulaire d'envoi** : `create-transfer-dialog.tsx`
   utilisait un `defaultValue` non réactif (React ne le réapplique qu'au montage). Ajout
   d'un `useEffect` qui synchronise la devise sur la collaboration choisie à chaque
   changement. Même correctif appliqué à `create-payment-dialog.tsx` par cohérence.
4. **Statut de validation des preuves absent** : ajout de `Proof.status`
   (`pending`/`validated`/`rejected`), migration `2b802e2505d4`, synchronisation
   automatique avec le statut de l'envoi/paiement parent lors de l'approbation, du rejet
   et de l'annulation. Affiché dans `ProofsCard` (badge).
5. **Notifications incomplètes** : ajout de `transfer_cancelled`/`payment_cancelled`
   (l'annulation par l'initiateur ne notifiait jamais l'autre partie) et
   `rate_proposed` (une proposition de taux collaboratif ne notifiait personne).

## Tests ajoutés

- `test_cancel_transfer_reverses_client_debt`, `test_reject_transfer_reverses_client_debt`,
  `test_reject_transfer_reverses_reliquat_client_credit` (`test_transfers.py`)
- `test_cancel_payment_reverses_client_debt`, `test_reject_payment_reverses_client_debt`
  (`test_payments.py`)
- `test_proof_status_pending_then_validated_on_transfer_approval`,
  `test_proof_status_rejected_on_transfer_rejection`,
  `test_proof_status_validated_on_payment_approval` (`test_proofs.py`)
- `test_rate_proposal_notifies_other_party` (`test_collaborations.py`)

Suite complète : **154 tests passent** (146 avant cette passe). `alembic check` : aucune
dérive. Build + lint frontend : clean.

## Fichiers modifiés

Backend :
`app/services/client_service.py`, `app/repositories/client_repository.py`,
`app/services/transfer_service.py`, `app/services/payment_service.py`,
`app/services/collaboration_service.py`, `app/models/notification.py`,
`app/models/proof.py`, `app/repositories/proof_repository.py`,
`app/schemas/proof.py`, `alembic/versions/2b802e2505d4_add_status_to_proofs.py`,
`app/tests/integration/test_transfers.py`, `app/tests/integration/test_payments.py`,
`app/tests/integration/test_proofs.py`, `app/tests/integration/test_collaborations.py`

Frontend :
`frontend/src/app/(app)/transfers/create-transfer-dialog.tsx`,
`frontend/src/app/(app)/payments/create-payment-dialog.tsx`,
`frontend/src/types/api.ts`, `frontend/src/components/proofs-card.tsx`

## Écarts restants (hors MVP ou différés délibérément)

- **Rapports mensuels / PDF / Excel / rapports par collaborateur, wallet, employé,
  fournisseur, client** : seul le rapport journalier (CSV) existe. Chantier de taille
  significative (nouvelle logique d'agrégation par période + dépendance PDF/XLSX),
  volontairement non traité dans cette passe faute de temps ; à planifier séparément.
- **Opérations nationales multi-devises avec taux de conversion** : la validation actuelle
  exige un équilibre strict par devise, ce qui empêche un échange réel entre deux devises
  différentes. Nécessite une migration (`rate`, `converted_amount` sur
  `NationalOperationLine`) — non traité ici.
- **Notifications email/SMS/WhatsApp** : explicitement listées "hors MVP" par le cahier
  des charges lui-même (§37.2). Non traité, conforme à la priorisation du cahier des
  charges.
- **Application mobile native** : hors MVP (§37.2), PWA responsive recommandée à la place
  — l'interface web actuelle est responsive mais n'est pas empaquetée en PWA installable.
- **Dashboard employé distinct** : l'employé voit le même schéma de dashboard que l'Owner,
  filtré par permissions au niveau des routes, plutôt qu'une vue vraiment simplifiée et
  dédiée comme décrit en §27.2. Écart mineur, non traité.
- **Type d'opération sur les taux privés** : le cahier des charges mentionne cette
  dimension comme optionnelle ("si nécessaire") ; non implémentée, jugé non bloquant.
- **Validation entreprise "en attente"** : le cahier des charges laisse le choix entre
  activation automatique ou en attente de validation (§8.2) ; seule l'activation
  automatique est implémentée.
