<p align="center">
  <img src="docs/assets/readme/cover.svg" alt="Tripwright: plan a trip around the places you want to visit" width="100%">
</p>

<p align="center">
  <a href="https://guide.dirtydev.cc">Live demo</a> ·
  <a href="docs/DEPLOYMENT.md">Deployment</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a> ·
  <a href="README.md">简体中文</a>
</p>

# Tripwright

A self-hosted travel planning agent for desktop browsers. Choose a city, find places through conversation, add them to a route, and compare walking and driving directions on the map. Each trip keeps its conversations, saved places and routes so you can return to it later.

The current interface and documentation are primarily in Chinese. Place search and directions use AMap and are intended mainly for destinations in China.

[![Conversation, editable stops and the route map in one workspace](docs/assets/readme/routes.webp)](docs/assets/readme/routes.webp)

## Live demo

Visit the [public demo](https://guide.dirtydev.cc). Select a city and start exploring without logging in, granting location access or uploading a photo.

The demo has usage limits and is intended for brief trials. Avoid uploading sensitive photos or personal information. Registration and login are available; email verification and password recovery are not yet available on the demo.

## Travel planning

- Choose a destination and browse attractions, neighborhoods and accommodation locations with photos and addresses. Save a place, add it to a route, or ask the guide about it.
- Keep conversations alongside travel resources and maps. Search messages, edit questions, delete messages or ask again; affected older answers are marked after edits.
- Search and add stops directly in a route, change their order, and compare walking and driving directions. Stops survive a failed route calculation.
- Start as a guest and save the trip to an account later. Keep separate trips and reopen them after signing in.
- Optionally upload a reference photo, confirm the recognized place, and request a guide card.
- Choose a server-configured model and adjust thinking with a stepped slider. Available levels depend on the model's capabilities. Each task keeps its original selection across retries. See [model configuration](docs/MODELS.md).
- Open curated travel links and Bilibili search links.

[![City selection and the planning entry point](docs/assets/readme/home.webp)](docs/assets/readme/home.webp)

## Self-hosting

Use Docker Engine and Compose v2. You need a domain pointing at your server, an OpenAI Chat Completions-compatible model endpoint, AMap Web Service credentials and a separate AMap JavaScript key. Email verification and password recovery require SMTP.

Clone the repository:

```bash
git clone https://github.com/DirtyDidsDoneDerCheap2049/AI_Guide.git
cd AI_Guide
```

From the repository root, create `.env` only if it does not already exist:

```bash
cp -n deploy/.env.production.example .env
chmod 600 .env
nano .env
```

Set database credentials, a random session secret, model and AMap settings, `SITE_ADDRESS` and `PUBLIC_BASE_URL`. Keep `IMAGE_REGISTRY=local` to build from source. Variable details are in the [deployment guide](docs/DEPLOYMENT.md).

```bash
docker compose -f docker-compose.yml -f deploy/compose.small.yml config --quiet
docker compose -f docker-compose.yml -f deploy/compose.small.yml pull mysql redis
docker compose -f docker-compose.yml -f deploy/compose.small.yml build api
docker compose -f docker-compose.yml -f deploy/compose.small.yml build web
docker compose -f docker-compose.yml -f deploy/compose.small.yml up -d
```

The small profile uses one Worker process with two threads. Builds run separately to reduce concurrent memory demand. The migration container should exit with code 0 before the API starts. Caddy serves the frontend and obtains an HTTPS certificate.

The application has been deployed on Ubuntu 24.04 with 2 GB RAM. Server configuration and maintenance instructions are in the [deployment guide](docs/DEPLOYMENT.md).

## Architecture

Vue 3 and TypeScript provide the UI. FastAPI validates requests, ownership and versions. MySQL stores trips, messages, routes, task states and events; Redis provides the task queue and short-lived caching. Dramatiq Workers execute model tasks with bounded retries, leases and recovery. SSE delivers persisted events with a reconnect cursor.

See [architecture](docs/ARCHITECTURE.md) and [local development](docs/DEMO-STARTUP.md) for code entry points and checks.

For existing deployments, follow the update section in the [deployment guide](docs/DEPLOYMENT.md#更新). Preserve your configuration and data volumes when upgrading.

## Limitations

- Intended mainly for desktop browsers and destinations in China, with place data, photos and routes provided by AMap. Check prices, opening hours and booking rules with the venue.
- Travel resources link to curated articles and Bilibili searches; the application does not parse arbitrary articles or video content.
- Only server-allowlisted models are available. Other providers need compatible Chat Completions parameters, structured output and image support.
- Email verification and password recovery require SMTP. The development `console` mode does not deliver email.
- Booking, payments, turn-by-turn navigation and a separate mobile app are not supported.

## License

Source code is licensed under [MIT](LICENSE). Maps, place photos and third-party marks shown in screenshots retain their respective ownership; see [image notes](docs/assets/readme/README.md). Do not include credentials or personal data in issues; see [security](SECURITY.md).
