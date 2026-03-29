"""
Legacy service layer (Phase 5 retirement).

Vehicle-specific service functions have been superseded by the pluggable
provider system in `my_garage.services.collection_services`.
This module is retained only to avoid breaking any imports of VehicleServiceError.
"""


class VehicleServiceError(Exception):
    """Raised when a vehicle-specific service operation fails.

    Kept for backwards-compatibility; new code should use the collection
    services provider pattern instead.
    """
