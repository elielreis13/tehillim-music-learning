"""Re-exporta de tehillim.core para compatibilidade."""
from tehillim.core.supabase import (
    sb_headers, sb_get, sb_post, sb_put, sb_patch, sb_upsert, sb_delete,
    get_user_from_token,
)
from tehillim.core.auth import (
    get_current_user, is_teacher_session, is_owner_session,
    require_teacher, require_teacher_token, require_owner_token,
    get_student_teacher_id, assert_student_owner,
)
from tehillim.core.activity import log_activity, activity_scope

__all__ = [
    "sb_headers", "sb_get", "sb_post", "sb_put", "sb_patch", "sb_upsert", "sb_delete",
    "get_user_from_token", "get_current_user", "is_teacher_session", "is_owner_session",
    "require_teacher", "require_teacher_token", "require_owner_token",
    "get_student_teacher_id", "assert_student_owner",
    "log_activity", "activity_scope",
]
