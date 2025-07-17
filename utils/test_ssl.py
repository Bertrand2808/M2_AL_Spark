#!/usr/bin/env python3
import ssl
import socket
import sys

def test_ssl_connection():
    try:
        print("Testing SSL connection to Kafka...")
        
        # Créer un contexte SSL
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Tenter la connexion
        with socket.create_connection(("kafka", 9093), timeout=10) as sock:
            with ssl_context.wrap_socket(sock, server_hostname="kafka") as ssock:
                print(f"SSL connection successful!")
                print(f"SSL version: {ssock.version()}")
                print(f"Cipher: {ssock.cipher()}")
                return True
                
    except Exception as e:
        print(f"SSL connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ssl_connection()
    sys.exit(0 if success else 1)
