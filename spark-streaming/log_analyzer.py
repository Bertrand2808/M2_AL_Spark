from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import argparse

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

    # Initialisation Spark
    spark = SparkSession.builder \
        .appName("LogAnalyzer") \
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
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
        # Lecture depuis Kafka
        raw_logs = spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", args.kafka_broker) \
            .option("subscribe", "http-logs") \
            .option("startingOffsets", "latest") \
            .load()

        # Parsing JSON et filtrage des erreurs
        logs = raw_logs.select(
            from_json(col("value").cast("string"), log_schema).alias("log")
        ).select("log.*") \
         .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSSX")) \
         .filter(col("status") >= 400)
    else:
        # Mode local - lecture TCP
        lines = spark \
            .readStream \
            .format("socket") \
            .option("host", "localhost") \
            .option("port", 9999) \
            .load()

        logs = lines.select(
            from_json(col("value"), log_schema).alias("log")
        ).select("log.*") \
         .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSSX")) \
         .filter(col("status") >= 400)

    # Ajout d'une fenêtre temporelle pour les métriques
    windowed_metrics = logs \
        .withWatermark("timestamp", "10 seconds") \
        .groupBy(
            window(col("timestamp"), "30 seconds"),
            col("status")
        ) \
        .agg(
            count("*").alias("error_count"),
            approx_count_distinct("ip").alias("unique_ips"),
            collect_list("url").alias("error_urls")
        )

    # Alertes
    alerts = windowed_metrics \
        .filter(col("error_count") > 100) \
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

    if args.mode == "production":
        # Envoi des alertes vers Kafka
        alert_query = alerts \
            .select(to_json(struct("*")).alias("value")) \
            .writeStream \
            .outputMode("append") \
            .format("kafka") \
            .option("kafka.bootstrap.servers", args.kafka_broker) \
            .option("topic", "alerts") \
            .option("checkpointLocation", "checkpoint/alerts") \
            .trigger(processingTime="10 seconds") \
            .start()
    else:
        # Mode local - affichage console
        alert_query = alerts.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime="10 seconds") \
            .start()

    # Sauvegarde des erreurs
    errors_as_json = logs.select(to_json(struct("*")).alias("value"))

    error_query = errors_as_json.writeStream \
        .outputMode("append") \
        .format("text") \
        .option("path", "output/errors") \
        .option("checkpointLocation", "checkpoint/errors") \
        .trigger(processingTime="10 seconds") \
        .start()

    # Affichage des métriques en temps réel
    metrics_query = windowed_metrics \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .trigger(processingTime="10 seconds") \
        .start()

    # Attendre l'arrêt des streams
    error_query.awaitTermination()
    metrics_query.awaitTermination()
    alert_query.awaitTermination()

if __name__ == "__main__":
    main()
