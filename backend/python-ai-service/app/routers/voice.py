"""
Voice router — thin shim that re-exports from app.voice.router.
All voice logic lives in app/voice/ (JarvisVoice MN+EN system).
"""
from app.voice.router import router  # noqa: F401
