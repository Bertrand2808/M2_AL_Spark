# Procedure

## Générer des logs

Le script génère par défaut des logs en JSON (plus facile à parser) avec :

- Horodatage ISO 8601 UTC
- IP aléatoire
- Méthode parmi GET, POST, PUT, DELETE
- URL /resource/1 à /resource/N (par défaut N=10)
- Code HTTP 200/404/500 selon la répartition 90/5/5 %
- Taux configurable via --rate et choix du format (--format json|csv)

```bash
python .\utils\genlogs_v2.py --urls 1000 --rate 1000 --format json #1000 logs par seconde
python .\utils\genlogs_v2.py # 1 log par seconde
```
