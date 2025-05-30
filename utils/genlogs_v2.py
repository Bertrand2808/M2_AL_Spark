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
    args = parser.parse_args()

    # Préparation des listes
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

if __name__ == "__main__":
    main()
