# LDS Connect

Plateforme numérique de la **Ligue de la Souveraineté** (football, Burkina Faso) :
registre des équipes et joueurs, licences numériques à QR code, calendrier, feuille de match
numérique, classements et site public installable (PWA).

Proposée par LUPORA Group. Le code est portable et auto-hébergeable : l'hébergement est
choisi par la Ligue.

> Projet en cours de démarrage — la documentation complète arrive avec les prochaines étapes.

## Démarrage rapide (Docker)

```bash
git clone <ce-dépôt> lds-connect && cd lds-connect
make env        # crée .env et génère les clés
make dev        # lance la pile (laisser tourner, puis ouvrir un 2e terminal)
make migrate    # crée les tables
make seed       # charge la saison 2027, les 20 équipes et des comptes de test
```

- Site : http://localhost:3000
- API (documentation interactive) : http://localhost:8000/docs
- Courriels (Mailpit) : http://localhost:8025
- SMS et paiements simulés : http://localhost:8090

`make help` liste toutes les commandes.
