# TrustMesh — Astro Frontend (Phase 0)

Multi-tenant SaaS frontend for TrustMesh, built with Astro + Tailwind CSS v4.

## Dev server

```sh
npm run dev
```

Starts on **port 4321** (configured in `astro.config.mjs`).

- Vite dashboard (legacy): port 5173
- FastAPI backend: port 8000

## Project Structure

```text
/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   └── styles/
│       └── global.css    # Tailwind v4 entry point + @theme placeholder
├── astro.config.mjs
└── package.json
```

## Commands

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
