from cryptography.fernet import Fernet
import os

class CredentialManager:
    def __init__(self):
        # Generate key once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        self.cipher = Fernet(os.getenv('ENCRYPTION_KEY').encode())

    def encrypt_credentials(self, api_key: str, api_secret: str) -> tuple:
        encrypted_key = self.cipher.encrypt(api_key.encode())
        encrypted_secret = self.cipher.encrypt(api_secret.encode())
        return encrypted_key, encrypted_secret

    def get_decrypted(self, encrypted_key: bytes, encrypted_secret: bytes) -> tuple:
        return (
            self.cipher.decrypt(encrypted_key).decode(),
            self.cipher.decrypt(encrypted_secret).decode()
        )