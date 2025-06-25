from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import argparse
import os
import shutil
import time
import uuid

def main():
    parser = argparse.ArgumentParser(description="Analyseur de logs HTTP")
    parser.add_argument(
        "--mode", choices=["local", "production"], default="local",
        help="Mode d'exécution: local (TCP) ou production (Kafka)"
    )
    parser.add_argument(
        "--kafka-broker", default="kafka:9092",
        help="Adresse du broker Kafka"
    )
    args = parser.parse_args()

    print(f"Démarrage en mode: {args.mode}")

    # Créer des checkpoints uniques avec UUID pour éviter les conflits
    unique_id = str(uuid.uuid4())[:8]
    
    # Nettoyage complet des checkpoints pour éviter les erreurs d'offset
    if args.mode == "production":
        checkpoint_base = f"/app/checkpoint/{unique_id}"
        
        # Nettoyage sécurisé pour les volumes Docker
        try:
            if os.path.exists("/app/checkpoint"):
                print("Nettoyage des checkpoints existants...")
                # Ne pas supprimer le répertoire racine monté, seulement son contenu
                for item in os.listdir("/app/checkpoint"):
                    item_path = os.path.join("/app/checkpoint", item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                print("Checkpoints nettoyés avec succès")
        except Exception as e:
            print(f"Attention: Impossible de nettoyer les checkpoints: {e}")
            print("Continuons avec des nouveaux répertoires...")
        
        # Attendre que Kafka soit prêt
        print("Attente de Kafka...")
        time.sleep(15)
    else:
        checkpoint_base = f"checkpoint/{unique_id}"
        try:
            if os.path.exists("checkpoint"):
                print("Nettoyage complet des checkpoints...")
                shutil.rmtree("checkpoint")
        except Exception as e:
            print(f"Attention: Impossible de nettoyer les checkpoints: {e}")

    # Initialisation Spark avec configuration optimisée
    spark = SparkSession.builder \
        .appName(f"LogAnalyzer-{unique_id}") \
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Schema pour les logs JSON
    log_schema = StructType([
        StructField("timestamp", StringType(), True),
        StructField("ip", StringType(), True),
        StructField("method", StringType(), True),
        StructField("url", StringType(), True),
        StructField("status", IntegerType(), True)
    ])

    if args.mode == "production":
        print(f"Connexion à Kafka: {args.kafka_broker}")
        # Lecture depuis Kafka avec configuration robuste
        raw_logs = spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", args.kafka_broker) \
            .option("subscribe", "http-logs") \
            .option("startingOffsets", "earliest") \
            .option("failOnDataLoss", "false") \
            .option("kafka.consumer.group.id", f"log-analyzer-{unique_id}") \
            .option("kafka.consumer.group.id", f"log-analyzer-{unique_id}") \
            .option("maxOffsetsPerTrigger", "500") \
            .option("kafka.session.timeout.ms", "30000") \
            .option("kafka.request.timeout.ms", "40000") \
            .load()

        # Parsing JSON avec gestion d'erreurs robuste
        logs = raw_logs \
            .selectExpr("CAST(value AS STRING) as json_string") \
            .select(from_json(col("json_string"), log_schema).alias("log")) \
            .select("log.*") \
            .filter(col("timestamp").isNotNull() & col("status").isNotNull()) \
            .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'")) \
            .filter(col("timestamp").isNotNull()) \
            .filter(col("status") >= 400)
    else:
        print("Connexion TCP localhost:9999")
        lines = spark \
            .readStream \
            .format("socket") \
            .option("host", "localhost") \
            .option("port", 9999) \
            .load()

        logs = lines \
            .select(from_json(col("value"), log_schema).alias("log")) \
            .select("log.*") \
            .filter(col("timestamp").isNotNull() & col("status").isNotNull()) \
            .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'")) \
            .filter(col("timestamp").isNotNull()) \
            .filter(col("status") >= 400)

    # Metrics avec watermark
    windowed_metrics = logs \
        .withWatermark("timestamp", "30 seconds") \
        .groupBy(
            window(col("timestamp"), "30 seconds"),
            col("status")
        ) \
        .agg(
            count("*").alias("error_count"),
            approx_count_distinct("ip").alias("unique_ips"),
            collect_list("url").alias("error_urls")
        )

    # Alertes - seuil réduit pour test
    alerts = windowed_metrics \
        .filter(col("error_count") > 5) \
        .withColumn("alert", lit("ALERTE : Nombre d'erreurs élevé")) \
        .withColumn("alert_timestamp", current_timestamp()) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("status"),
            col("error_count"),
            col("unique_ips"),
            col("alert"),
            col("alert_timestamp")
        )

    # Démarrage des streams avec gestion d'erreurs simplifiée
    queries = []

    try:
        # Stream 1: Affichage des métriques
        print("Démarrage du stream des métriques...")
        metrics_query = windowed_metrics \
            .writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .option("checkpointLocation", f"{checkpoint_base}/metrics") \
            .trigger(processingTime="15 seconds") \
            .start()
        queries.append(metrics_query)

        # Stream 2: Gestion des alertes
        if args.mode == "production":
            print("Démarrage du stream d'alertes vers Kafka...")
            alert_query = alerts \
                .select(to_json(struct("*")).alias("value")) \
                .writeStream \
                .outputMode("append") \
                .format("kafka") \
                .option("kafka.bootstrap.servers", args.kafka_broker) \
                .option("topic", "alerts") \
                .option("checkpointLocation", f"{checkpoint_base}/alerts") \
                .trigger(processingTime="15 seconds") \
                .start()
        else:
            print("Démarrage du stream d'alertes console...")
            alert_query = alerts \
                .writeStream \
                .outputMode("append") \
                .format("console") \
                .option("truncate", False) \
                .option("checkpointLocation", f"{checkpoint_base}/alerts") \
                .trigger(processingTime="15 seconds") \
                .start()
        queries.append(alert_query)

        # Stream 3: Sauvegarde des erreurs
        print("Démarrage du stream de sauvegarde...")
        errors_as_json = logs.select(to_json(struct("*")).alias("value"))
        error_query = errors_as_json \
            .writeStream \
            .outputMode("append") \
            .format("text") \
            .option("path", "output/errors") \
            .option("checkpointLocation", f"{checkpoint_base}/errors") \
            .trigger(processingTime="15 seconds") \
            .start()
        queries.append(error_query)

        print("Tous les streams sont démarrés. En attente...")

        # Attendre tous les streams
        for query in queries:
            query.awaitTermination()

    except Exception as e:
        print(f"Erreur dans le streaming: {e}")
        # Arrêter proprement tous les streams
        for query in queries:
            if query.isActive:
                query.stop()
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
