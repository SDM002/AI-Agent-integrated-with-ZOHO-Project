"""Per-request user context — thread-safe isolation via contextvars."""
import contextvars

# --- Context Variables (Isolated per async request) ---
USER_ID: contextvars.ContextVar[str] = contextvars.ContextVar("USER_ID", default="")
REQUEST_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar("REQUEST_CONTEXT", default="")

#Set User Context 
def set_user_id(user_id: str) -> None:
    USER_ID.set(user_id)  # Assign user ID to current request context


def get_user_id() -> str:
    return USER_ID.get()  # Retrieve user ID for current request

# Set Request Metadata Context
def set_request_context(context: str) -> None:
    REQUEST_CONTEXT.set(context)  # Assign contextual info (date, user email, etc.)


def get_request_context() -> str:
    return REQUEST_CONTEXT.get()  # Retrieve contextual info for current request
