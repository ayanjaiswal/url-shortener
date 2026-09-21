import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # base62: a-z, A-Z, 0-9
CODE_LENGTH = 7  # 62**7 is about 3.5 trillion possible codes


def generate_code() -> str:
    """Random, unguessable short code (secrets uses the OS's secure random generator)."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def is_valid_code(code: str) -> bool:
    """Cheap format check so junk paths never reach the database."""
    return len(code) == CODE_LENGTH and all(c in ALPHABET for c in code)
