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
            producer = KafkaProducer(
                bootstrap_servers=[args.kafka_broker],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            print(f"Connexion à Kafka: {args.kafka_broker}, topic: {args.kafka_topic}")
        except ImportError:
            print("Error: kafka-python package required for production mode")
            print("Install with: pip install kafka-python")
            return
        except Exception as e:
            print(f"Error connecting to Kafka: {e}")
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
                if random.randint(1, 100) == 1:  # Log occasionally
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
            producer.close()

if __name__ == "__main__":
    main()
