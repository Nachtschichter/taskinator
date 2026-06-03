"""
Taskinator Security Utilities

Shared password hashing, verification, and validation.
Uses Argon2id as the primary scheme with bcrypt fallback
for backward compatibility with existing hashes.
"""
from passlib.context import CryptContext

# Argon2id primary; bcrypt fallback for existing hashes.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated=["bcrypt"],
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=1,
    argon2__hash_len=32,
    argon2__type="ID",
)


def hash_password(password: str) -> str:
    """Hash a plain-text password using the configured CryptContext."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    return pwd_context.verify(plain, hashed)


def validate_password_strength(password: str) -> bool:
    """Minimum password policy: at least 8 characters."""
    return len(password) >= 8
