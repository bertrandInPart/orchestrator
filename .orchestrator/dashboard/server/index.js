import express from "express";
import path from "node:path";
import { existsSync } from "node:fs";
import { boardRouter } from "./routes/board.js";
import { featureRouter } from "./routes/feature.js";
import { REPO_ROOT } from "./config.js";

const PORT = process.env.DASHBOARD_PORT ?? 4000;

const app = express();
app.use(express.json());
app.use("/api", boardRouter);
app.use("/api", featureRouter);

// In production (`npm start`), serve the built client alongside the API from
// this same process. In dev (`npm run dev`), Vite serves the client
// separately and proxies /api/* here instead — see client/vite.config.ts.
const clientDist = path.join(REPO_ROOT, ".orchestrator", "dashboard", "client", "dist");
if (existsSync(clientDist)) {
  app.use(express.static(clientDist));
  app.get(/^(?!\/api).*/, (req, res) => {
    res.sendFile(path.join(clientDist, "index.html"));
  });
}

app.listen(PORT, () => {
  console.log(`Orchestrator dashboard API listening on http://localhost:${PORT}`);
  if (!existsSync(clientDist)) {
    console.log(
      "No built client found — run `npm run dev` (from .orchestrator/dashboard) for the " +
        "Vite dev server, or `npm run build` first for a production-style single-process run."
    );
  }
});
