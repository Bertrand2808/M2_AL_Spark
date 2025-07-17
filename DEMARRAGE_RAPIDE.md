# Guide de Démarrage Rapide 🚀

## Lancement en une commande

```bash
# Aller dans le répertoire du projet
cd /home/ds/0_workspace/_VSCode/Python/traitement_dist/M2_AL_Spark

# Lancer tout l'environnement SSL
docker-compose up -d
```

## Vérification que tout fonctionne ✅

### 1. Vérifier les services
```bash
docker-compose ps
```
**Attendu** : Tous les services doivent être `Up` et `healthy`

### 2. Accéder à Kafka UI
- Ouvrir http://localhost:8080 dans votre navigateur
- Vous devriez voir l'interface Kafka UI avec SSL configuré
- Vérifier que les topics `http-logs` et `alerts` sont visibles

### 3. Voir les logs en temps réel
```bash
# Logs de l'analyseur Spark
docker-compose logs -f log-analyzer

# Logs du générateur de logs
docker-compose logs -f log-generator
```

## Services disponibles 📊

| Service | URL/Commande | Description |
|---------|--------------|-------------|
| **Kafka UI** | http://localhost:8080 | Interface de monitoring SSL ✅ |
| **Zookeeper** | Port 2181 | Coordination Kafka |
| **Kafka SSL** | Port 9093 | Message broker avec SSL |
| **Log Generator** | `docker-compose logs log-generator` | Génère des logs HTTP |
| **Log Analyzer** | `docker-compose logs log-analyzer` | Analyse avec Spark Streaming |

## Architecture du système 🏗️

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Log Generator  │───▶│  Kafka (SSL)    │───▶│  Log Analyzer   │
│  (Python)       │    │  Topic:         │    │  (Spark Stream) │
│                 │    │  http-logs      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                        │
                               ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Kafka UI      │    │  Topic: alerts  │
                       │ (Port 8080)     │    │ (Seuil >100)    │
                       └─────────────────┘    └─────────────────┘
```

## Commandes utiles 🛠️

### Arrêter tout
```bash
docker-compose down
```

### Redémarrer un service spécifique
```bash
docker-compose restart kafka-ui
docker-compose restart log-analyzer
```

### Nettoyer complètement (en cas de problème)
```bash
docker-compose down -v
docker system prune -f
docker-compose up -d
```

### Voir les topics Kafka
```bash
docker-compose exec kafka kafka-topics --bootstrap-server kafka:9093 \
  --command-config /etc/kafka/secrets/client.properties --list
```

### Lire les messages du topic http-logs
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9093 \
  --consumer.config /etc/kafka/secrets/client.properties \
  --topic http-logs --from-beginning
```

## Métriques attendues 📈

Le système génère automatiquement :
- **50 logs/seconde** par défaut
- **Erreurs 4xx/5xx** filtrées et analysées
- **Alertes** quand > 100 erreurs en 30 secondes
- **Agrégations** par fenêtres de 30 secondes

## Problèmes résolus ✅

### Kafka UI + SSL
- **Problème** : `NoSuchFileException: /secrets/spark.client.keystore.jks`
- **Solution** : Correction du montage des volumes SSL
- **Statut** : ✅ Résolu - Kafka UI fonctionne parfaitement

## Documentation complète 📚

- **Configuration SSL** : `doc/README_SSL.md`
- **Procédure détaillée** : `doc/procedure.md`
- **Documentation générale** : `doc/Documentation.pdf`
