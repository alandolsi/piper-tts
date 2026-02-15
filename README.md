# Piper TTS Service

## Build

```bash
docker compose build
```

## Run

```bash
docker compose up -d
```

## Health Check

```bash
curl -i http://localhost:8000/health
```

## TTS Request

```bash
curl -sS -X POST http://localhost:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hallo, dies ist ein Test mit Piper."}' \
  --output out.wav
```

## TTS Request (same text uses cache)

```bash
curl -sS -X POST http://localhost:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hallo, dies ist ein Test mit Piper."}' \
  --output out_cached.wav
```

## Coolify

- Deploy with Docker Compose using this repository.
- Expose service port `8000`.
- Keep `/cache` mapped to persistent storage.

## Voice Tuning

- `PIPER_LENGTH_SCALE`: speaking speed (`>1.0` slower, `<1.0` faster)
- `PIPER_NOISE_SCALE`: voice variation (lower is more stable)
- `PIPER_NOISE_W`: phoneme variation (lower is cleaner)
- `PIPER_SPEAKER`: speaker id (for multi-speaker models)
