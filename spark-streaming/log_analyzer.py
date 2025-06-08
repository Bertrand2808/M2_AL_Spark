from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json

def main():
    # Initialisation Spark
    spark = SparkSession.builder \
        .appName("LogAnalyzer") \
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
    
    # Lecture du stream TCP
    lines = spark \
        .readStream \
        .format("socket") \
        .option("host", "localhost") \
        .option("port", 9999) \
        .load()
    
    # Parsing JSON et filtrage des erreurs (status >= 400)
    logs = lines.select(
        from_json(col("value"), log_schema).alias("log")
    ).select("log.*") \
     .withColumn("timestamp", to_timestamp(col("timestamp"))) \
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
    
    # on déclenche des alertes si on a trop d'erreurs 
    alerts = windowed_metrics \
        .filter(col("error_count") > 100) \
        .withColumn("alert",lit("ALERTE : Nombre d'erreurs élevé"))
    alert_query=alerts.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate",False) \
        .trigger(processingTime="10 seconds") \
        .start()

    # Sauvegarde des erreurs brutes dnas un fichier
    error_query = logs.writeStream \
        .outputMode("append") \
        .format("json") \
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