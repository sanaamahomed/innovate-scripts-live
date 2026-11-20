"""Dev only: run the app with fake transcription and fake Claude so the UI can be tried without keys or models."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ANTHROPIC_API_KEY", "mock")
import uvicorn, server
from tests.test_app import fake_claude  # noqa
import time
def slow_tx(p, prog=lambda f: None):
    for f in (0.2, 0.6, 1): prog(f); time.sleep(0.4)
    return [{"spk": "unknown", "text": t, "t": i * 4.0} for i, t in enumerate(["Good day, is this Mr Dlamini? You're speaking to Sam from Innovate on behalf of Netstar.", "Yes.", "This call is recorded. The Early Warning with StarTag is R259 a month.", "Okay, sounds good."])]
server.stt.transcribe = slow_tx
server.engine.call_claude = fake_claude
uvicorn.run(server.app, port=8123)
