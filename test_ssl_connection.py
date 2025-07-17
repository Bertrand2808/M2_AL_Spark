#!/usr/bin/env python3
"""
Script de test pour vérifier la connectivité SSL avec Kafka
"""
import sys
import os

def test_kafka_ssl_connection():
    try:
        from kafka import KafkaProducer, KafkaConsumer
        from kafka.errors import KafkaError
        import json
        
        # Configuration SSL
        ssl_config = {
            'bootstrap_servers': ['kafka:9093'],
            'security_protocol': 'SSL',
            'ssl_keystore_location': '/secrets/spark.client.keystore.jks',
            'ssl_keystore_password': 'password',
            'ssl_key_password': 'password',
            'ssl_truststore_location': '/secrets/spark.client.truststore.jks',
            'ssl_truststore_password': 'password',
            'ssl_check_hostname': False,
            'ssl_cafile': '/secrets/ca.crt'
        }
        
        print("Test de connexion SSL à Kafka...")
        print(f"Bootstrap servers: {ssl_config['bootstrap_servers']}")
        
        # Test du producteur
        producer = KafkaProducer(
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            **ssl_config
        )
        
        # Envoi d'un message de test
        test_message = {
            "test": True,
            "message": "Test SSL connection",
            "timestamp": "2025-01-01T12:00:00Z"
        }
        
        future = producer.send('http-logs', value=test_message)
        record_metadata = future.get(timeout=10)
        
        print(f"✅ Message envoyé avec succès!")
        print(f"   Topic: {record_metadata.topic}")
        print(f"   Partition: {record_metadata.partition}")
        print(f"   Offset: {record_metadata.offset}")
        
        producer.close()
        
        # Test du consommateur
        consumer = KafkaConsumer(
            'http-logs',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='ssl-test-group',
            consumer_timeout_ms=5000,
            **ssl_config
        )
        
        print("✅ Consommateur SSL créé avec succès!")
        consumer.close()
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except KafkaError as e:
        print(f"❌ Erreur Kafka: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        return False

def check_ssl_files():
    """Vérifier que les fichiers SSL sont présents"""
    required_files = [
        '/secrets/ca.crt',
        '/secrets/spark.client.keystore.jks',
        '/secrets/spark.client.truststore.jks'
    ]
    
    print("Vérification des fichiers SSL...")
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - présent")
        else:
            print(f"❌ {file_path} - manquant")
            return False
    return True

if __name__ == "__main__":
    print("=== Test de configuration SSL Kafka ===")
    
    if not check_ssl_files():
        print("❌ Fichiers SSL manquants. Veuillez exécuter le script generate_ssl_secrets.sh")
        sys.exit(1)
    
    if test_kafka_ssl_connection():
        print("🎉 Configuration SSL OK!")
        sys.exit(0)
    else:
        print("❌ Problème de configuration SSL")
        sys.exit(1)
