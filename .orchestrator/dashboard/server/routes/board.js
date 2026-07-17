import { Router } from "express";
import { loadConfig } from "../config.js";
import * as githubAdapter from "../adapters/github.js";
import * as jiraAdapter from "../adapters/jira.js";

function adapterFor(config) {
  return config.provider === "github" ? githubAdapter : jiraAdapter;
}

export const boardRouter = Router();

// GET /api/board -> normalized list of every feature currently on the board,
// across every Stage, from whichever provider .orchestrator/config.yml
// selects.
boardRouter.get("/board", async (req, res) => {
  try {
    const config = loadConfig();
    const adapter = adapterFor(config);
    const features = await adapter.listFeatures(config);
    res.json({ provider: config.provider, features });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});
