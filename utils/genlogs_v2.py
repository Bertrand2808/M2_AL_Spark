#!/usr/bin/env python3
import random
import time
import argparse
import json
from datetime import datetime

def random_ip():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))

def main():
    parser = argparse.ArgumentParser(
        description="Générateur minimal de logs HTTP"
    )
    parser.add_argument(
        "--urls", type=int, default=10,
        help="Nombre d'URLs différentes à simuler"
    )
    parser.add_argument(
        "--rate", type=float, default=1.0,
        help="Taux de génération de logs (logs par seconde)"
    )
    parser.add_argument(
        "--format", choices=["csv", "json"], default="json",
        help="Format de sortie des logs"
    )
    parser.add_argument(
        "--methods", nargs='+', default=["GET", "POST", "PUT", "DELETE"],
        help="Liste des méthodes HTTP à utiliser"
    )
    parser.add_argument(
        "--status-dist", nargs=3, type=int, default=[90, 5, 5],
        metavar=("OK", "NOTFOUND", "ERROR"),
        help="Répartition en pourcentages pour les codes 200, 404, 500"
    )
    parser.add_argument(
        "--mode", choices=["local", "production"], default="local",
        help="Mode d'exécution: local (stdout) ou production (Kafka)"
    )
    parser.add_argument(
        "--kafka-broker", default="kafka:9092",
        help="Adresse du broker Kafka"
    )
    parser.add_argument(
        "--kafka-topic", default="http-logs",
        help="Topic Kafka pour les logs"
    )
    args = parser.parse_args()

    # Import Kafka seulement si nécessaire
    if args.mode == "production":
        try:
            from kafka import KafkaProducer
            import ssl
            import os
            
            # Attendre que Kafka soit prêt
            print("Attente de Kafka...")
            time.sleep(10)
            
            # Déterminer le protocole basé sur le port
            if ":9093" in args.kafka_broker:
                # Port SSL
                ssl_keystore = "/secrets/spark.client.keystore.jks"
                if os.path.exists(ssl_keystore):
                    print("Configuration SSL détectée pour port 9093")
                    # Configuration SSL simplifiée pour kafka-python
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    # Charger le certificat CA si disponible
                    try:
                        ssl_context.load_verify_locations(cafile='/secrets/ca.crt')
                    except:
                        pass  # Ignorer si le fichier n'existe pas
                    
                    producer = KafkaProducer(
                        bootstrap_servers=[args.kafka_broker],
                        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                        security_protocol='SSL',
                        ssl_context=ssl_context,
                        retries=5,
                        retry_backoff_ms=1000,
                        request_timeout_ms=30000,
                        max_block_ms=60000
                    )
                    print(f"Connexion à Kafka SSL: {args.kafka_broker}, topic: {args.kafka_topic}")
                else:
                    print("Erreur: Port 9093 mais pas de certificats SSL")
                    return
            else:
                # Port PLAINTEXT (9092)
                print("Mode PLAINTEXT détecté (port 9092)")
                producer = KafkaProducer(
                    bootstrap_servers=[args.kafka_broker],
                    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                    security_protocol='PLAINTEXT',
                    retries=5,
                    retry_backoff_ms=1000,
                    request_timeout_ms=30000,
                    max_block_ms=60000
                )
                print(f"Connexion à Kafka PLAINTEXT: {args.kafka_broker}, topic: {args.kafka_topic}")
                
        except ImportError:
            print("Error: kafka-python package required for production mode")
            print("Install with: pip install kafka-python")
            return
        except Exception as e:
            print(f"Error connecting to Kafka: {e}")
            import traceback
            traceback.print_exc()
            return

    urls = [f"/resource/{i}" for i in range(1, args.urls + 1)]
    status_codes = [200, 404, 500]
    status_weights = args.status_dist

    interval = 1.0 / args.rate if args.rate > 0 else 0

    try:
        while True:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "ip": random_ip(),
                "method": random.choice(args.methods),
                "url": random.choice(urls),
                "status": random.choices(status_codes, weights=status_weights, k=1)[0]
            }
            
            if args.mode == "production":
                producer.send(args.kafka_topic, value=entry)
                # Flush périodiquement pour s'assurer de l'envoi
                if random.randint(1, 10) == 1:  # Flush tous les 10 messages environ
                    producer.flush()
                    print(f"Sent to Kafka: {entry}")
            else:
                if args.format == "json":
                    print(json.dumps(entry), flush=True)
                else:
                    # CSV délimité par ;
                    print(
                        f"{entry['timestamp']};{entry['ip']};{entry['method']};"
                        f"{entry['url']};{entry['status']}",
                        flush=True
                    )
            if interval:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nArrêt du générateur de logs.")
        if args.mode == "production":
            producer.flush()
            producer.close()

if __name__ == "__main__":
    main()
