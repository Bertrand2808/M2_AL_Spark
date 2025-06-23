FROM bitnami/spark:3.5.0

USER root

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY log_analyzer.py /app/

WORKDIR /app

CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", "--master", "local[*]", "log_analyzer.py", "--mode", "production"]
