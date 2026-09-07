"""
Encryption for MongoDB-persisted data:
  - encrypt/decrypt : string-level Fernet for OAuth tokens in user_tokens collection
  - FernetCipher    : bytes-level adapter for LangGraph EncryptedSerializer
                      encrypts all checkpoint data (user messages, AI replies, tool calls)
                      before it hits the checkpoints + checkpoint_writes collections
"""
from cryptography.fernet import Fernet, InvalidToken
from app.config import SETTINGS

fernet: Fernet | None = None


def get_fernet() -> Fernet:
    global fernet
    if fernet is None:
        fernet = Fernet(SETTINGS.ENCRYPTION_KEY.encode())
    return fernet

def encrypt(value: str) -> str:
    """Encrypt a string with Fernet — used for OAuth tokens."""
    if not value:
        return value
    return get_fernet().encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    """Decrypt a Fernet token string back to plaintext."""
    if not value:
        return value
    try:
        return get_fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        return value


class FernetCipher:
    """
    Adapter matching LangGraph's CipherProtocol interface.

    Actual CipherProtocol (verified from langgraph source):
        encrypt(plaintext: bytes) -> tuple[str, bytes]   # (cipher_name, ciphertext)
        decrypt(ciphername: str, ciphertext: bytes) -> bytes

    Reuses the same ENCRYPTION_KEY as OAuth token encryption.
    Pass to EncryptedSerializer(cipher=FernetCipher()) in MongoDBSaver setup.
    """

    def encrypt(self, plaintext: bytes) -> tuple[str, bytes]:
        return "fernet", get_fernet().encrypt(plaintext)

    def decrypt(self, ciphername: str, ciphertext: bytes) -> bytes:
        return get_fernet().decrypt(ciphertext)
