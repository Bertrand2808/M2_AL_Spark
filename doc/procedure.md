# Procedure

## Modes d'exécution

Le système supporte deux modes d'exécution :
- **Local** : Utilise TCP/netcat comme précédemment
- **Production** : Utilise Kafka pour la communication entre services

## Mode Local (TCP)

### Générer des logs

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

### Lancement avec redirection vers netcat pour creer un stream TCP
```bash
python ./utils/genlogs_v2.py --urls 1000 --rate 1000 --format json | nc -lk 9999
```

ou dans ubuntu :
```bash
python3 ./utils/genlogs_v2.py --urls 1000 --rate 1000 --format json | nc -lk 9999
```

pour générer uniquement des erreurs 500 :

```bash
python3 ./utils/genlogs_v2.py --urls 1000 --rate 1000 --format json --status-dist 0 0 100 | nc -lk 9999
```

### Analyse des logs avec Spark Streaming (Mode Local)

Le script `log_analyzer.py` analyse en temps réel les logs générés et effectue les tâches suivantes :

#### Fonctionnalités
- **Connexion TCP** : Se connecte au stream netcat sur le port 9999
- **Filtrage des erreurs** : Capture uniquement les logs avec status HTTP >= 400 (erreurs 4xx et 5xx)
- **Analyse temporelle** : Agrège les métriques par fenêtres de 30 secondes
- **Métriques calculées** :
  - Nombre total d'erreurs par type de status
  - Nombre approximatif d'IPs uniques générant des erreurs
  - Liste des URLs en erreur
- **Sauvegarde** : Stocke toutes les erreurs au format JSON dans `output/errors/`
- **Affichage temps réel** : Affiche les métriques agrégées toutes les 30 secondes

#### Lancement de l'analyse

Il faut lancer deux terminaux distincts.

Dans le premier, la commande suivante doit être jouée :
```bash
python ./utils/genlogs_v2.py --urls 1000 --rate 100 --format json | nc -lk 9999
```

Dans le second terminal, vous avez deux options :
1. via le script `run_spark_streaming.sh` qui nettoie les anciens fichiers et lance l'analyse proprement
2. via `spark-submit` directement

**Option 1 (recommandée) - Via le script `run_spark_streaming.sh`**
```bash
chmod +x ./run_spark_streaming.sh
./run_spark_streaming.sh
```

**Option 2 - Via `spark_submit`**
```bash
spark-submit ./spark-streaming/log_analyzer.py --mode local
```

## Mode Production (Kafka + Docker)

### Prérequis
- Docker et Docker Compose installés
- Ports 9092 (Kafka) disponibles

### Lancement complet avec Docker Compose

```bash
# Lancer l'infrastructure complète
docker-compose up -d

# Voir les logs en temps réel
docker-compose logs -f log-analyzer

# Arrêter tous les services
docker-compose down
```

### Architecture en mode production

1. **Zookeeper** : Coordination pour Kafka
2. **Kafka** : Message broker avec topics `http-logs` et `alerts`
3. **Kafka UI** : Interface web pour monitoring Kafka (http://localhost:8080)
4. **Log Generator** : Génère des logs HTTP et les envoie au topic `http-logs`
5. **Log Analyzer** : 
   - Lit les logs depuis le topic `http-logs`
   - Analyse les erreurs et génère des métriques
   - Envoie les alertes au topic `alerts` quand > 100 erreurs/30s

### Interface de monitoring Kafka UI

Une interface web est disponible sur http://localhost:8080 pour :
- Visualiser les topics et leurs partitions
- Consulter les messages en temps réel
- Surveiller les consommateurs et producteurs
- Gérer la configuration Kafka

### Commandes utiles pour le debugging

```bash
# Accéder à l'interface Kafka UI
# Ouvrir http://localhost:8080 dans votre navigateur

# Voir les topics Kafka
docker exec -it $(docker-compose ps -q kafka) kafka-topics --bootstrap-server localhost:9092 --list

# Lire les messages du topic http-logs
docker exec -it $(docker-compose ps -q kafka) kafka-console-consumer --bootstrap-server localhost:9092 --topic http-logs --from-beginning

# Lire les alertes
docker exec -it $(docker-compose ps -q kafka) kafka-console-consumer --bootstrap-server localhost:9092 --topic alerts --from-beginning

# Redémarrer un service spécifique
docker-compose restart log-generator
docker-compose restart log-analyzer

# Nettoyer complètement en cas de problème
docker-compose down -v
docker system prune -f
docker-compose up -d
```

### Résolution des problèmes courants

#### Erreur "Expected e.g. {\"topicA\":{\"0\":23,\"1\":-1}}, got -1"
Cette erreur survient en cas de problème avec les offsets Kafka. Solution :
```bash
# Arrêter tous les services
docker-compose down -v

# Supprimer les volumes et checkpoints
sudo rm -rf ./checkpoint ./output

# Redémarrer
docker-compose up -d
```

#### Services qui ne démarrent pas correctement
```bash
# Vérifier l'état des services
docker-compose ps

# Voir les logs détaillés
docker-compose logs kafka
docker-compose logs log-analyzer

# Redémarrer un service spécifique
docker-compose restart log-analyzer
```

#### Performance lente
Le taux de génération de logs est réduit à 50 logs/seconde par défaut pour éviter la surcharge. Pour l'augmenter, modifier le docker-compose.yml :
```yaml
log-generator:
  # ...existing code...
  command: ["python", "genlogs_v2.py", "--mode", "production", "--rate", "100", "--urls", "1000", "--kafka-broker", "kafka:9092"]
```

### Personnalisation des paramètres

Pour modifier le taux de génération ou autres paramètres, éditer le `docker-compose.yml` :

```yaml
log-generator:
  # ...existing code...
  command: ["python", "genlogs_v2.py", "--mode", "production", "--rate", "500", "--urls", "2000", "--kafka-broker", "kafka:9092"]
```

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

### Format des alertes envoyées au topic alerts
```json
{
  "window_start": "2025-05-30T18:52:30.000Z",
  "window_end": "2025-05-30T18:53:00.000Z",
  "status": 404,
  "error_count": 150,
  "unique_ips": 25,
  "alert": "ALERTE : Nombre d'erreurs élevé",
  "alert_timestamp": "2025-05-30T18:53:05.123Z"
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
