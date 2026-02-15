import asyncio
import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

MODEL_PATH = Path(os.getenv("PIPER_MODEL_PATH", "/models/de_DE-eva_k-x-low.onnx"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", "/cache"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("piper-tts")

app = FastAPI(title="Piper TTS API", version="1.0.0")

_lock_registry: Dict[str, asyncio.Lock] = {}
_registry_guard = asyncio.Lock()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _lock_for_key(key: str) -> asyncio.Lock:
    async with _registry_guard:
        lock = _lock_registry.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _lock_registry[key] = lock
        return lock


async def _synthesize_to_file(text: str, output_path: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "piper",
        "--model",
        str(MODEL_PATH),
        "--output_file",
        str(output_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate(input=text.encode("utf-8"))

    if process.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error_msg or "Piper synthesis failed")


@app.on_event("startup")
async def startup_event() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        logger.error("Model file not found at %s", MODEL_PATH)
        raise RuntimeError(f"Model file not found: {MODEL_PATH}")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.post("/tts")
async def tts(payload: TTSRequest) -> FileResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    key = _text_hash(text)
    cached_wav = CACHE_DIR / f"{key}.wav"

    if cached_wav.exists():
        return FileResponse(path=cached_wav, media_type="audio/wav", filename="speech.wav")

    lock = await _lock_for_key(key)
    async with lock:
        if cached_wav.exists():
            return FileResponse(path=cached_wav, media_type="audio/wav", filename="speech.wav")

        fd, tmp_name = tempfile.mkstemp(prefix=f"tts-{key}-", suffix=".wav", dir=str(CACHE_DIR))
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            await _synthesize_to_file(text=text, output_path=tmp_path)
            tmp_path.replace(cached_wav)
            return FileResponse(path=cached_wav, media_type="audio/wav", filename="speech.wav")
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to synthesize speech")
            raise HTTPException(status_code=500, detail="TTS synthesis failed") from exc
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    logger.warning("Failed to remove temporary file: %s", tmp_path)
