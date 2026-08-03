"""生产级声纹识别（见 docs/architecture/11-voiceprint.md）。"""

from app.services.voice.voiceprint.service import (
    VoiceprintError,
    create_voiceprint,
    delete_sample,
    delete_voiceprint,
    enroll_voiceprint,
    identify_voiceprint,
    list_samples,
    list_voiceprints,
    probe_voiceprint,
    update_voiceprint,
    verify_voiceprint,
)
from app.services.voice.voiceprint.store_pg import (
    InMemoryProfileStore,
    PostgresProfileStore,
    configure_profile_store,
    get_profile_store,
)
from app.services.voice.voiceprint.store_qdrant import (
    InMemoryVectorIndex,
    configure_vector_index,
    get_vector_index,
)

__all__ = [
    "InMemoryProfileStore",
    "InMemoryVectorIndex",
    "PostgresProfileStore",
    "VoiceprintError",
    "configure_profile_store",
    "configure_vector_index",
    "create_voiceprint",
    "delete_sample",
    "delete_voiceprint",
    "enroll_voiceprint",
    "get_profile_store",
    "get_vector_index",
    "identify_voiceprint",
    "list_samples",
    "list_voiceprints",
    "probe_voiceprint",
    "update_voiceprint",
    "verify_voiceprint",
]
