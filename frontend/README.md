# Sentinel — UEBA V2.1 SOC console

React 19 + Vite analyst workstation for the UEBA backend.

```bash
npm install
npm run dev            # http://localhost:5173
```

Set `VITE_API_BASE` to point at the backend (default `http://localhost:8000`).

## Data modes

Every request reports where its data came from, shown in the top-bar pill:

| Source        | When                                             | UI                         |
|---------------|--------------------------------------------------|----------------------------|
| `live`        | backend answered                                 | `LIVE · API`               |
| `demo`        | backend unreachable                              | `DEMO DATASET` (sample data from `src/data/demo.js`) |
| `not_exposed` | backend is up but the route doesn't exist        | "Route not exposed" panel naming the missing endpoint |
| `empty`       | route exists but has no record for that id       | "No profile" notice        |

Attack chains, investigation cases and behaviour profiles are served by
`backend/app/routers/investigation.py` (`GET /attack-chains`, `GET /cases`,
`GET /profiles/{user_id}`) and written on each `POST /logs/user` upload.
Chains are only stored once `StageMapper` assigns a stage other than UNKNOWN.

## Stack

- `@xyflow/react` — kill-chain graph
- `recharts` — activity, event mix, CTMC state radar
- `cmdk` — Ctrl/⌘ K command palette
- `framer-motion`, `sonner`, `lucide-react`
- Type: Chakra Petch (display), Schibsted Grotesk (UI), Martian Mono (data)
