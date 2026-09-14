# Waste Classification System

Authenticated waste-image classification MVP for Shema and Brenda's college project.

## First release

- Register and log in with email and password.
- Upload one JPG, PNG or WebP image up to 5 MB.
- Classify glass, metal, general trash, organic, paper or plastic.
- Show confidence, all class probabilities and disposal guidance.
- Mark predictions below 70% confidence as uncertain.

The web app never calls the model directly. It calls the NestJS API, which enforces authentication and forwards the validated image to the private Python classifier.

```text
Next.js web -> NestJS API -> FastAPI classifier -> MobileNetV2
                         -> PostgreSQL users
```

## Baseline model

The first vertical slice uses the MIT-licensed MobileNetV2 baseline at:

https://huggingface.co/karthikeya09/smart_image_recognation

Its `non-recyclable` output is presented as `general trash`. This third-party validation result is not the dissertation's final measured result. Replace the artifact with the team's evaluated model before reporting final Chapter Four metrics.

## Start with Docker

The first classifier startup downloads and caches the model, so it requires internet access and can take several minutes.

```bash
docker compose up --build
```

Open `http://localhost:3000`, create an account, and upload an image. Services:

- Web: `http://localhost:3000`
- API: `http://localhost:4000`
- API health: `http://localhost:4000/health`
- Classifier health: `http://localhost:8000/health`

## Run without Docker

Start PostgreSQL, then:

```bash
corepack enable
pnpm install
pnpm dev
```

In another terminal:

```bash
cd apps/classifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API expects these variables when it is run directly:

```bash
DATABASE_URL=postgresql://waste:waste@localhost:5432/waste
JWT_SECRET=local-development-secret-change-me
FRONTEND_URL=http://localhost:3000
CLASSIFIER_URL=http://localhost:8000
```

## Dokploy

1. Point `WEB_DOMAIN` and `API_DOMAIN` DNS A records to the Hetzner server.
2. Create a Dokploy Compose application using `docker-compose.dokploy.yml`.
3. Add `POSTGRES_PASSWORD`, `JWT_SECRET`, `WEB_DOMAIN` and `API_DOMAIN` in Dokploy Environment.
4. Ensure the external `dokploy-network` exists.
5. Deploy. PostgreSQL and the model cache use named volumes.

The classifier and PostgreSQL are private services. Only the web and API services are routed through Traefik.

## Current authentication boundary

This MVP uses an Argon2id password hash and a 24-hour bearer access token. Refresh tokens, email verification, password reset, SMS and account administration are intentionally deferred until the classification flow is accepted.

