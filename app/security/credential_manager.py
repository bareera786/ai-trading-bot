from cryptography.fernet import Fernet
import os

class CredentialManager:
    def __init__(self):
        # Generate key once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            print("⚠️ WARNING: ENCRYPTION_KEY not found in environment! Credential Manager will use a temporary unsafe key.")
            # Use a dummy key to prevent crash on import, but crypto will fail if validating against different key
            key = Fernet.generate_key().decode()
            
        self.cipher = Fernet(key.encode() if hasattr(key, 'encode') else str(key).encode())

    def encrypt_credentials(self, api_key: str, api_secret: str) -> tuple:
        encrypted_key = self.cipher.encrypt(api_key.encode())
        encrypted_secret = self.cipher.encrypt(api_secret.encode())
        return encrypted_key, encrypted_secret

    def get_decrypted(self, encrypted_key: bytes, encrypted_secret: bytes) -> tuple:
        return (
            self.cipher.decrypt(encrypted_key).decode(),
            self.cipher.decrypt(encrypted_secret).decode()
        )