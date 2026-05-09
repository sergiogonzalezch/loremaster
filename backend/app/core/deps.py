# Backward compatibility - re-exports from database.dependencies
from app.core.database.dependencies import (
    get_collection_or_404,
    get_collection_or_404_owned,
    get_entity_or_404,
    get_entity_or_404_owned,
    get_document_or_404,
    get_current_db_user,
)
