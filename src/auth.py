from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str
    role: str
    organization_id: int


def get_current_user() -> User:
    """
    Returns the active user. Hardcoded for single-user MVP.
    Swap this implementation for Supabase Auth when going multi-user.
    """
    return User(
        id=1,
        name="Finance Director",
        email="finance@yourorg.org",
        role="admin",
        organization_id=1,
    )
