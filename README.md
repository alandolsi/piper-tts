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
