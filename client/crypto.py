#!/usr/bin/env python3
"""
Módulo de criptografía para PyScale
"""

import base64
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
from typing import Optional

class PyScaleCrypto:
    """Manejo de criptografía para PyScale"""
    
    def __init__(self, private_key_b64: Optional[str] = None):
        if private_key_b64:
            private_bytes = base64.b64decode(private_key_b64)
            self.private_key = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
        else:
            self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
    
    def get_public_key_b64(self) -> str:
        """Obtener clave pública en base64"""
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_bytes).decode('utf-8')
    
    def get_private_key_b64(self) -> str:
        """Obtener clave privada en base64"""
        private_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        return base64.b64encode(private_bytes).decode('utf-8')
    
    def derive_shared_key(self, peer_public_key_b64: str) -> bytes:
        """Derivar clave compartida usando ECDH (X25519)"""
        try:
            peer_public_bytes = base64.b64decode(peer_public_key_b64)
            peer_public_key = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
            
            # Intercambio de claves ECDH
            shared_secret = self.private_key.exchange(peer_public_key)
            
            # Derivar clave usando HKDF
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,  # 256 bits para ChaCha20-Poly1305
                salt=None,
                info=b'pyscale-key-derivation',
                backend=default_backend()
            ).derive(shared_secret)
            
            return derived_key
        except Exception as e:
            raise ValueError(f"Error deriving shared key: {str(e)}")
    
    def encrypt_message(self, message: str, shared_key: bytes) -> dict:
        """Encriptar mensaje usando ChaCha20-Poly1305"""
        try:
            # Generar nonce único (96 bits)
            nonce = os.urandom(12)
            
            # Crear cifrador
            chacha = ChaCha20Poly1305(shared_key)
            
            # Encriptar
            encrypted_data = chacha.encrypt(nonce, message.encode('utf-8'), None)
            
            return {
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'ciphertext': base64.b64encode(encrypted_data).decode('utf-8'),
                'algorithm': 'chacha20-poly1305'
            }
        except Exception as e:
            raise ValueError(f"Error encrypting message: {str(e)}")
    
    def decrypt_message(self, encrypted_data: dict, shared_key: bytes) -> str:
        """Desencriptar mensaje"""
        try:
            nonce = base64.b64decode(encrypted_data['nonce'])
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            
            chacha = ChaCha20Poly1305(shared_key)
            decrypted_data = chacha.decrypt(nonce, ciphertext, None)
            
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Error decrypting message: {str(e)}")
    
    @staticmethod
    def generate_preshared_key() -> str:
        """Generar una clave precompartida para WireGuard"""
        return base64.b64encode(os.urandom(32)).decode('utf-8')
