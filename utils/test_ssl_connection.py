#!/usr/bin/env python3
import ssl
import socket
import sys

def test_ssl_connection():
    try:
        print("Testing SSL connection to Kafka...")
        
        # Créer un contexte SSL
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.load_verify_locations(cafile='/secrets/ca.crt')
        
        # Se connecter
        sock = socket.create_connection(('kafka', 9093), timeout=10)
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname='kafka')
        
        print(f"✅ SSL connection successful!")
        print(f"SSL version: {ssl_sock.version()}")
        print(f"Cipher: {ssl_sock.cipher()}")
        
        ssl_sock.close()
        return True
        
    except Exception as e:
        print(f"❌ SSL connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ssl_connection()
    sys.exit(0 if success else 1)
