# Backward compatibility - re-exports from database.utils
from app.core.database.utils import (
    paginate,
    paginate_with_sort,
    db_commit,
    get_active_by_id,
    list_active_by_collection,
    list_active_paginated,
)
from app.core.database.soft_delete import soft_delete
