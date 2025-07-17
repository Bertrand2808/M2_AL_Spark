FROM bitnami/spark:3.5.0

USER root

# Install curl for downloading JARs
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Download Kafka connector JARs using curl
RUN curl -L -o /opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar \
    https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar

RUN curl -L -o /opt/bitnami/spark/jars/kafka-clients-3.4.0.jar \
    https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar

RUN curl -L -o /opt/bitnami/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar \
    https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar

RUN curl -L -o /opt/bitnami/spark/jars/commons-pool2-2.11.1.jar \
    https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# Configuration JVM pour optimiser la mémoire
ENV SPARK_DRIVER_MEMORY=1g
ENV SPARK_EXECUTOR_MEMORY=1g
ENV PYSPARK_DRIVER_PYTHON=python3
ENV PYSPARK_PYTHON=python3
# Options JVM pour limiter la consommation mémoire
ENV SPARK_SUBMIT_OPTS="-Xmx1g -Xms512m -XX:MaxMetaspaceSize=256m"

COPY log_analyzer.py /app/

WORKDIR /app

CMD ["python", "log_analyzer.py", "--mode", "production"]
