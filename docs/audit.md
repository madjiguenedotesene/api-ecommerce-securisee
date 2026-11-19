# Rapport d'audit – API e-commerce v1 (novembre 2025)

**Périmètre** : code de la version 1 (FastAPI, SQLModel, JWT), testé en local sur une base SQLite jetable.
**Méthode** : revue de code, preuves de concept (`scripts/poc_version_origine.py`), analyse statique (bandit), audit des dépendances (pip-audit).

## Preuves de concept sur la version d'origine

```
V1 | Le premier inscrit devient administrateur | is_admin=True
V2 | Mot de passe d'un caractère accepté | HTTP 201
V3 | Un simple client crée un produit | HTTP 201
V3 | Un simple client crée une variante | HTTP 201
V4 | Commande de quantité -500 | HTTP 500, stock passé de 10 à 510
V5 | Commande invalide refusée mais enregistrée vide | 1 commande(s) vide(s) en base
V3 | Un simple client supprime un produit | HTTP 200
V6 | 30 mots de passe faux d'affilée | codes [401] (aucun blocage)
V7 | Empreintes de mots de passe écrites dans les journaux | 2 occurrence(s)
```

## Détail et correctifs

| # | Faille | Cause dans le code d'origine | Correctif (version 2) | Test |
|---|---|---|---|---|
| V1 | Prise de contrôle à l'installation | `is_admin = (aucun utilisateur en base)` à l'inscription : sur un déploiement neuf, le premier visiteur devient administrateur | aucun rôle attribué par inscription ; administrateur initial créé au démarrage depuis `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `test_V1_*` |
| V2 | Mots de passe faibles | aucune contrainte sur `password` | 12 caractères minimum, 3 types de caractères | `test_V2_*` |
| V3 | Contrôle d'accès par fonction absent (BFLA) | produits et variantes protégés par `get_current_user` (tout client connecté) au lieu de l'administrateur | dépendance `exiger_admin` sur toutes les écritures du catalogue ; refus journalisés | `test_V3_*` |
| V4 | Manipulation du stock | `OrderItemCreate.quantity` sans borne : une quantité négative augmente le stock (la réponse plante en 500, mais l'écriture est déjà faite) | `1 ≤ quantity ≤ 100`, au plus 50 lignes par commande | `test_V4_*` |
| V5 | Commandes fantômes | la commande est validée en base avant la vérification des lignes | toutes les lignes vérifiées avant toute écriture, une seule transaction, `SELECT … FOR UPDATE` sur le stock | `test_V5_*` |
| V6 | Force brute sur `/token` | aucune limite | 5 échecs par couple identifiant / IP en 15 min → 429 ; temps de réponse constant pour un identifiant inconnu | `test_V6_*` |
| V7 | Secrets dans les journaux | `create_engine(echo=True)` journalise chaque requête SQL, empreintes bcrypt comprises | `echo=False` ; journal d'audit applicatif dédié | `test_V7_*` |
| V8 | Dépendances vulnérables | 27 avis de sécurité dans 8 paquets (starlette, python-multipart, pyasn1, ecdsa, python-jose…) ; python-jose n'a pas de version corrigée | PyJWT à la place de python-jose, versions à jour, `pip-audit` en CI | CI |

## Durcissements supplémentaires

- Clé de signature et URL de base **obligatoires** (plus de valeur par défaut faible) ; clé d'au moins 32 caractères.
- Jetons JWT avec `exp` et `iat` obligatoires, algorithme imposé : un jeton signé avec une autre clé ou `alg: none` est refusé (test).
- Statuts de commande limités à une liste fermée ; prix et stock positifs.
- En-têtes `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store`.
- Image Docker exécutée sans privilèges root ; port exposé sur 127.0.0.1 ; CORS désactivé par défaut.
- Le lien fournisseur et le stock restent invisibles des clients (vues publique et administrateur distinctes, déjà présentes dans la v1).

## Bug trouvé pendant les essais

Avec plusieurs processus gunicorn, chaque processus créait l'administrateur au démarrage : le second plantait sur la contrainte d'unicité. L'initialisation est maintenant sérialisée par un verrou consultatif PostgreSQL ; démarrage vérifié avec 4 processus.

## Limites connues

- Le limiteur de tentatives est en mémoire : il compte par processus. En production multi-instances, il faut un stockage partagé (Redis) ou une limitation au niveau du proxy.
- Pas de révocation de jeton avant expiration (30 min) ni de jeton de rafraîchissement.
