"""Multi-tenant install profiles — MPLAT-SPR-08."""

from .profiles import (
    InstallProfile,
    ProfileError,
    active_profile_id,
    apply_active_profile,
    load_install_profile,
    validate_secrets_path,
)

__all__ = [
    "InstallProfile",
    "ProfileError",
    "active_profile_id",
    "apply_active_profile",
    "load_install_profile",
    "validate_secrets_path",
]