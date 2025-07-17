# Configuration SSL pour Kafka et Spark Streaming

## Démarrage rapide ⚡

Pour lancer l'environnement complet avec SSL configuré :

```bash
# 1. Aller dans le répertoire du projet
cd /home/ds/0_workspace/_VSCode/Python/traitement_dist/M2_AL_Spark

# 2. Lancer tous les services
docker-compose up -d

# 3. Vérifier que tous les services sont en cours d'exécution
docker-compose ps

# 4. Accéder à Kafka UI (SSL configuré automatiquement)
# Ouvrir http://localhost:8080 dans votre navigateur

# 5. Voir les logs en temps réel
docker-compose logs -f log-analyzer
```

**Interfaces disponibles** :
- 🌐 **Kafka UI** : http://localhost:8080 (Interface de monitoring SSL)
- 📊 **Logs Spark Streaming** : `docker-compose logs -f log-analyzer`
- 📝 **Logs générateur** : `docker-compose logs -f log-generator`

## Prérequis

1. **Générer les certificats SSL** (si pas encore fait) :
```bash
chmod +x generate_ssl_secrets.sh
./generate_ssl_secrets.sh
```

2. **Vérifier que le dossier `./secrets` contient** :
- `ca.crt` - Certificat de l'autorité de certification
- `kafka.server.keystore.jks` - Keystore du serveur Kafka
- `kafka.server.truststore.jks` - Truststore du serveur Kafka
- `spark.client.keystore.jks` - Keystore du client Spark
- `spark.client.truststore.jks` - Truststore du client Spark
- `client.properties` - Configuration SSL pour les clients Kafka
- `password` - Fichier de mot de passe (requis par Kafka)
- `keystore_password` - Mot de passe du keystore
- `truststore_password` - Mot de passe du truststore
- `key_password` - Mot de passe des clés privées

## Configuration des services

### Docker Compose

Les services ont été configurés pour utiliser SSL :

- **Kafka** : Écoute uniquement sur le port 9093 en SSL
- **Log Generator** : Configure pour envoyer via SSL
- **Log Analyzer** : Configure pour lire/écrire via SSL
- **Kafka UI** : Configure pour se connecter en SSL

### Variables d'environnement importantes

```yaml
# Kafka SSL Configuration
KAFKA_LISTENERS: SSL://0.0.0.0:9093
KAFKA_ADVERTISED_LISTENERS: SSL://kafka:9093
KAFKA_SSL_KEYSTORE_LOCATION: /secrets/kafka.server.keystore.jks
KAFKA_SSL_KEYSTORE_PASSWORD: password
```

## Commandes pour démarrer

### 1. Démarrage complet
```bash
docker-compose up -d
```

### 2. Démarrage par étapes (recommandé pour le debug)
```bash
# 1. Démarrer Zookeeper et Kafka
docker-compose up -d zookeeper kafka

# 2. Attendre que Kafka soit prêt, puis créer les topics
docker-compose up kafka-topics-setup

# 3. Démarrer le générateur de logs
docker-compose up -d log-generator

# 4. Démarrer l'analyseur Spark
docker-compose up -d log-analyzer

# 5. Démarrer Kafka UI
docker-compose up -d kafka-ui
```

### 3. Test de connectivité SSL
```bash
# Tester la connexion SSL avec les outils Kafka
docker-compose exec kafka kafka-topics --bootstrap-server kafka:9093 \
  --command-config /etc/kafka/secrets/client.properties --list

# Tester avec le script de test (si disponible)
docker-compose run --rm log-generator python /app/test_ssl_connection.py

# Vérifier que Kafka accepte les connexions SSL
docker-compose exec kafka-topics-setup kafka-topics --bootstrap-server kafka:9093 \
  --command-config /etc/kafka/secrets/client.properties --list
```

## Accès aux interfaces

- **Kafka UI** : http://localhost:8080 ✅ **Entièrement fonctionnel avec SSL**
- **Logs Spark** : `docker-compose logs log-analyzer`
- **Logs générateur** : `docker-compose logs log-generator`

### Problème résolu : Kafka UI et SSL

**Problème initial** : Kafka UI ne pouvait pas accéder aux fichiers SSL car le montage des volumes pointait vers `/etc/kafka/secrets` mais la configuration cherchait dans `/secrets`.

**Solution appliquée** : Modification du montage des volumes dans `docker-compose.yml` :
```yaml
kafka-ui:
  # ...
  volumes:
    - ./secrets:/secrets:ro  # ✅ Correct - pointe vers /secrets
  # au lieu de:
  # - ./secrets:/etc/kafka/secrets:ro  # ❌ Incorrect
```

**Vérification** : Après redémarrage, Kafka UI peut maintenant accéder aux certificats SSL et se connecter à Kafka.

## Configuration Spark Streaming pour SSL

### Dans le code Python (PySpark)
```python
raw_logs = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9093") \
    .option("subscribe", "http-logs") \
    .option("kafka.security.protocol", "SSL") \
    .option("kafka.ssl.keystore.location", "/secrets/spark.client.keystore.jks") \
    .option("kafka.ssl.keystore.password", "password") \
    .option("kafka.ssl.key.password", "password") \
    .option("kafka.ssl.truststore.location", "/secrets/spark.client.truststore.jks") \
    .option("kafka.ssl.truststore.password", "password") \
    .load()
```

### Via spark-submit (hors Docker)
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --conf spark.kafka.bootstrap.servers=localhost:9093 \
  --conf spark.kafka.security.protocol=SSL \
  --conf spark.kafka.ssl.keystore.location=./secrets/spark.client.keystore.jks \
  --conf spark.kafka.ssl.keystore.password=password \
  --conf spark.kafka.ssl.key.password=password \
  --conf spark.kafka.ssl.truststore.location=./secrets/spark.client.truststore.jks \
  --conf spark.kafka.ssl.truststore.password=password \
  log_analyzer.py --mode production --kafka-broker localhost:9093
```

## Commandes de debug

### Vérifier les logs
```bash
# Logs Kafka
docker-compose logs kafka

# Logs Spark Streaming
docker-compose logs log-analyzer

# Logs générateur
docker-compose logs log-generator
```

### Tester la connectivité réseau
```bash
# Test de connectivité au port SSL
docker-compose exec log-generator nc -zv kafka 9093

# Vérifier les topics Kafka
docker-compose exec kafka kafka-topics --bootstrap-server kafka:9093 --list
```

### Redémarrer un service spécifique
```bash
docker-compose restart log-analyzer
docker-compose restart log-generator
```

## Gestion des mots de passe

### Développement
Les mots de passe sont définis dans :
- `generate_ssl_secrets.sh` : mot de passe `password`
- Variables d'environnement du docker-compose

### Production
Pour la production, remplacez les mots de passe hardcodés par :
- Variables d'environnement sécurisées
- Docker Secrets
- HashiCorp Vault
- AWS Secrets Manager
- Kubernetes Secrets

Exemple avec variables d'environnement :
```bash
export KEYSTORE_PASSWORD="your-secure-password"
export TRUSTSTORE_PASSWORD="your-secure-password"
```

## Troubleshooting

### ✅ Kafka UI - Problème de connexion SSL (RÉSOLU)

**Symptôme** : Erreur `NoSuchFileException: /secrets/spark.client.keystore.jks`

**Cause** : Mauvais montage des volumes dans kafka-ui (pointait vers `/etc/kafka/secrets` au lieu de `/secrets`)

**Solution appliquée** :
```yaml
# ✅ Configuration correcte dans docker-compose.yml
kafka-ui:
  volumes:
    - ./secrets:/secrets:ro
```

**Vérification** :
```bash
# Redémarrer kafka-ui après modification
docker-compose restart kafka-ui

# Vérifier les logs (ne doit plus afficher d'erreurs SSL)
docker-compose logs kafka-ui
```

### Erreur "Connection refused"
- Vérifiez que Kafka écoute sur le port 9093
- Vérifiez que les certificats sont montés correctement

### Erreur SSL
- Vérifiez que les fichiers `.jks` sont présents dans `/secrets`
- Vérifiez que les mots de passe correspondent
- Vérifiez les permissions des fichiers

### Performance
- Ajustez les paramètres mémoire dans docker-compose.yml
- Modifiez `maxOffsetsPerTrigger` dans log_analyzer.py
- Ajustez le taux de génération avec `--rate` dans log-generator
