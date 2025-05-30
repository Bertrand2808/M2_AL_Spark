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
 
### Lancement avec redirection ver netcat pour creer un stream TCP
```bash
python ./utils/genlogs_v2.py --urls 1000 --rate 1000 --format json | nc -lk 9999
```

## Analyse des logs avec Spark Streaming

Le script `log_analyzer.py` analyse en temps réel les logs générés et effectue les tâches suivantes :

### Fonctionnalités
- **Connexion TCP** : Se connecte au stream netcat sur le port 9999
- **Filtrage des erreurs** : Capture uniquement les logs avec status HTTP >= 400 (erreurs 4xx et 5xx)
- **Analyse temporelle** : Agrège les métriques par fenêtres de 30 secondes
- **Métriques calculées** :
  - Nombre total d'erreurs par type de status
  - Nombre approximatif d'IPs uniques générant des erreurs
  - Liste des URLs en erreur
- **Sauvegarde** : Stocke toutes les erreurs au format JSON dans `output/errors/`
- **Affichage temps réel** : Affiche les métriques agrégées toutes les 30 secondes

### Lancement de l'analyse

```bash
# Terminal 1 : Génération et streaming des logs
python ./utils/genlogs_v2.py --urls 1000 --rate 100 --format json | nc -lk 9999

# Terminal 2 : Analyse Spark Streaming
spark-submit ./spark-streaming/log_analyzer.py
```

### Sortie attendue
- **Console** : Métriques agrégées par fenêtre temporelle et status code
- **Fichiers** : Logs d'erreur sauvegardés dans `output/errors/` au format JSON
- **Checkpoints** : Points de contrôle Spark dans `checkpoint/errors/`

### Structure des données analysées
```json
{
  "timestamp": "2025-05-30T18:52:47.123456Z",
  "ip": "192.168.1.100",
  "method": "GET",
  "url": "/resource/42",
  "status": 404
}
```

### Exemple de métriques affichées
```
+------------------------------------------+------+-----------+----------+
|window                                    |status|error_count|unique_ips|
+------------------------------------------+------+-----------+----------+
|{2025-05-30 18:52:30, 2025-05-30 18:53:00}|404   |45         |12        |
|{2025-05-30 18:52:30, 2025-05-30 18:53:00}|500   |5          |3         |
+------------------------------------------+------+-----------+----------+
```