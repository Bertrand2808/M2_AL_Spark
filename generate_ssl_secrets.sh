#!/bin/bash

set -e

# === PARAMÈTRES ===
PASS="password"        # Mot de passe pour tous les keystores/truststores (modifiable)
DAYS=365               # Durée de validité des certificats (en jours)
DIR="./secrets"
CA_ALIAS="CARoot"

# === 1. Préparation ===
mkdir -p "$DIR"
cd "$DIR"

echo "Génération de la CA (certificat racine)..."
openssl genrsa -out ca.key 2048
openssl req -x509 -new -key ca.key -days $DAYS -out ca.crt -subj "/CN=Kafka-Root-CA"

# === 2. Broker Kafka ===
echo "Génération du keystore pour Kafka..."
keytool -genkey -alias kafka-broker -keystore kafka.server.keystore.jks \
  -keyalg RSA -storepass $PASS -keypass $PASS -dname "CN=kafka" -validity $DAYS

keytool -keystore kafka.server.keystore.jks -alias kafka-broker -certreq \
  -file kafka.csr -storepass $PASS -keypass $PASS

echo "Signature du certificat du broker Kafka..."
openssl x509 -req -CA ca.crt -CAkey ca.key -in kafka.csr \
  -out kafka.crt -days $DAYS -CAcreateserial

keytool -keystore kafka.server.keystore.jks -alias $CA_ALIAS -import \
  -file ca.crt -storepass $PASS -noprompt

keytool -keystore kafka.server.keystore.jks -alias kafka-broker -import \
  -file kafka.crt -storepass $PASS -noprompt

keytool -keystore kafka.server.truststore.jks -alias $CA_ALIAS -import \
  -file ca.crt -storepass $PASS -noprompt

# === 3. Client Spark ===
echo "Génération du keystore pour Spark..."
keytool -genkey -alias spark-client -keystore spark.client.keystore.jks \
  -keyalg RSA -storepass $PASS -keypass $PASS -dname "CN=spark" -validity $DAYS

keytool -keystore spark.client.keystore.jks -alias spark-client -certreq \
  -file spark.csr -storepass $PASS -keypass $PASS

echo "Signature du certificat du client Spark..."
openssl x509 -req -CA ca.crt -CAkey ca.key -in spark.csr \
  -out spark.crt -days $DAYS -CAcreateserial

keytool -keystore spark.client.keystore.jks -alias $CA_ALIAS -import \
  -file ca.crt -storepass $PASS -noprompt

keytool -keystore spark.client.keystore.jks -alias spark-client -import \
  -file spark.crt -storepass $PASS -noprompt

keytool -keystore spark.client.truststore.jks -alias $CA_ALIAS -import \
  -file ca.crt -storepass $PASS -noprompt

# === 4. Fichiers de configuration additionnels ===
echo "Création des fichiers de configuration SSL..."

# Fichier de configuration client pour Kafka
cat > client.properties << EOF
security.protocol=SSL
ssl.keystore.location=/etc/kafka/secrets/spark.client.keystore.jks
ssl.keystore.password=$PASS
ssl.key.password=$PASS
ssl.truststore.location=/etc/kafka/secrets/spark.client.truststore.jks
ssl.truststore.password=$PASS
ssl.endpoint.identification.algorithm=
EOF

# Fichiers de mots de passe pour Kafka (requis par certaines versions)
echo "$PASS" > password
echo "$PASS" > keystore_password
echo "$PASS" > truststore_password
echo "$PASS" > key_password

echo
echo "=== Terminé ! Tous les certificats, keystore et truststore sont dans le dossier $DIR ==="
echo "Mot de passe par défaut : $PASS"
echo "Fichiers créés :"
ls -l "$DIR"
