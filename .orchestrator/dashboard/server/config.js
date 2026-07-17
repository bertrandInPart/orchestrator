import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import YAML from "yaml";

// server/ -> dashboard/ -> .orchestrator/ -> <repo root>
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
export const ORCH_DIR = path.join(REPO_ROOT, ".orchestrator");
const CONFIG_PATH = path.join(ORCH_DIR, "config.yml");
const GITHUB_WORKFLOW_INSTRUCTIONS_PATH = path.join(
  REPO_ROOT,
  ".github",
  "instructions",
  "github-workflow.instructions.md"
);

/**
 * Reads and parses .orchestrator/config.yml, which records the ticket
 * provider (github|jira) and its provider-specific settings. See
 * .orchestrator/scripts/init-wizard.py's CONFIG_TEMPLATE for the exact shape
 * this file is generated from.
 */
export function loadConfig() {
  if (!existsSync(CONFIG_PATH)) {
    throw new ConfigError(
      `.orchestrator/config.yml not found at ${CONFIG_PATH}. Run ` +
        `.orchestrator/scripts/init-wizard.py once to generate it, or create it ` +
        `by hand (see that script's CONFIG_TEMPLATE for the expected shape).`
    );
  }

  const raw = readFileSync(CONFIG_PATH, "utf8");
  const parsed = YAML.parse(raw);

  const provider = parsed?.ticket_system?.provider;
  if (provider !== "github" && provider !== "jira") {
    throw new ConfigError(
      `.orchestrator/config.yml has an unrecognized ticket_system.provider ` +
        `(${JSON.stringify(provider)}) — expected "github" or "jira".`
    );
  }

  if (provider === "github") {
    const github = parsed.ticket_system.github ?? {};
    if (!github.owner || !github.repo) {
      throw new ConfigError(
        ".orchestrator/config.yml is missing ticket_system.github.owner/repo."
      );
    }
    const project = readGithubProjectReference();
    return {
      provider: "github",
      github: {
        owner: github.owner,
        repo: github.repo,
        issueLabels: github.issue_labels ?? [],
        projectOwner: project.owner ?? github.owner,
        projectNumber: project.number,
      },
    };
  }

  const jira = parsed.ticket_system.jira ?? {};
  if (!jira.base_url || !jira.project_key) {
    throw new ConfigError(
      ".orchestrator/config.yml is missing ticket_system.jira.base_url/project_key."
    );
  }
  return {
    provider: "jira",
    jira: {
      baseUrl: jira.base_url,
      projectKey: jira.project_key,
    },
  };
}

/**
 * The Projects v2 board owner/number aren't in config.yml — they're recorded
 * as plain-text reference values in github-workflow.instructions.md by a
 * human after running setup-github-project.sh once. Parse them from there.
 */
function readGithubProjectReference() {
  if (!existsSync(GITHUB_WORKFLOW_INSTRUCTIONS_PATH)) {
    return { owner: undefined, number: undefined };
  }
  const text = readFileSync(GITHUB_WORKFLOW_INSTRUCTIONS_PATH, "utf8");
  const ownerMatch = text.match(/PROJECT_OWNER\s*=\s*(\S+)/);
  const numberMatch = text.match(/PROJECT_NUMBER\s*=\s*(\d+)/);
  return {
    owner: ownerMatch?.[1],
    number: numberMatch ? Number(numberMatch[1]) : undefined,
  };
}

export class ConfigError extends Error {}
