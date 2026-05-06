from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate-limiter instance keyed by client IP.
# Register on the FastAPI app in main.py:
#   app.state.limiter = limiter
#   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
#   app.add_middleware(SlowAPIMiddleware)
limiter = Limiter(key_func=get_remote_address)
