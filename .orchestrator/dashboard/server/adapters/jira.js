// Jira adapter: normalizes Jira REST v3 ticket state into the same shared
// feature shape the GitHub adapter produces, so routes/frontend never branch
// on provider.
//
// Auth: JIRA_EMAIL + JIRA_API_TOKEN env vars (basic auth against the Jira
// Cloud REST API, per Atlassian's API token scheme).
//
// Field mapping: this integration adapts to an EXISTING Jira project's own
// workflow rather than requiring new custom fields (see
// .orchestrator/docs/jira-integration.md and jira-workflow.instructions.md):
// `status.name` -> stage (native workflow status, moved via
// update-jira-ticket.sh's transition lookup against `stage_status_map`),
// the `agent:<name>` label -> currentAgent (native Jira label, not
// assignee — assignee still represents whichever human/bot Jira account
// owns the issue, which is a separate concept from "which chain stage/agent
// runs next"). Feature Slug/Branch default to the issue key itself; only if
// JIRA_FEATURE_SLUG_FIELD / JIRA_FEATURE_BRANCH_FIELD env vars are set
// (pointing at a custom field ID this project already has, e.g.
// "customfield_10050") do we read those instead.

const META_RE = /<!--\s*meta:\s*agent=(\S+)\s+stage=(\S+)\s+status=(\S+)\s+timestamp=(\S+)\s*-->/;
const AGENT_LABEL_PREFIX = "agent:";


function requireCredentials() {
  const email = process.env.JIRA_EMAIL;
  const token = process.env.JIRA_API_TOKEN;
  if (!email || !token) {
    throw new Error(
      "JIRA_EMAIL and JIRA_API_TOKEN environment variables must both be set " +
        "to query the Jira REST API."
    );
  }
  return { email, token };
}

function authHeader() {
  const { email, token } = requireCredentials();
  return `Basic ${Buffer.from(`${email}:${token}`).toString("base64")}`;
}

async function jiraRequest(baseUrl, path) {
  const res = await fetch(`${baseUrl}${path}`, {
    headers: {
      Authorization: authHeader(),
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Jira API GET ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}

function slugFieldId() {
  return process.env.JIRA_FEATURE_SLUG_FIELD ?? null;
}

function branchFieldId() {
  return process.env.JIRA_FEATURE_BRANCH_FIELD ?? null;
}

function normalizeIssue(baseUrl, issue) {
  const slugField = slugFieldId();
  const branchField = branchFieldId();
  const slug = (slugField && issue.fields[slugField]) || issue.key;
  const labels = issue.fields.labels ?? [];
  const agentLabel = labels.find((l) => l.startsWith(AGENT_LABEL_PREFIX));
  const currentAgent = agentLabel ? agentLabel.slice(AGENT_LABEL_PREFIX.length) : null;
  return {
    slug,
    title: issue.fields.summary,
    stage: issue.fields.status?.name ?? "Backlog",
    currentAgent: currentAgent === "none" ? null : currentAgent,
    branch: (branchField && issue.fields[branchField]) || null,
    ticketId: issue.key,
    ticketUrl: `${baseUrl}/browse/${issue.key}`,
    updatedAt: issue.fields.updated,
  };
}

/**
 * Lists every feature ticket in the configured Jira project, normalized to
 * the same shape as the GitHub adapter's listFeatures().
 */
export async function listFeatures(config) {
  const { baseUrl, projectKey } = config.jira;
  const fields = ["summary", "status", "labels", "updated"];
  const slugField = slugFieldId();
  const branchField = branchFieldId();
  if (slugField) fields.push(slugField);
  if (branchField) fields.push(branchField);

  const features = [];
  let startAt = 0;
  const maxResults = 50;
  for (;;) {
    const data = await jiraRequest(
      baseUrl,
      `/rest/api/3/search?jql=${encodeURIComponent(
        `project=${projectKey} ORDER BY updated DESC`
      )}&startAt=${startAt}&maxResults=${maxResults}&fields=${fields.join(",")}`
    );
    for (const issue of data.issues) {
      features.push(normalizeIssue(baseUrl, issue));
    }
    startAt += data.issues.length;
    if (startAt >= data.total || data.issues.length === 0) break;
  }
  return features;
}

/**
 * Fetches and parses the comment activity feed for one feature's ticket,
 * extracting the `<!-- meta: ... -->` convention (rendered by agents as
 * plain text in Jira's comment body, since Jira comments aren't Markdown).
 */
export async function getFeatureComments(config, slug) {
  const features = await listFeatures(config);
  const feature = features.find((f) => f.slug === slug);
  if (!feature) {
    throw new Error(`No Jira issue found for feature slug "${slug}".`);
  }

  const { baseUrl } = config.jira;
  const data = await jiraRequest(
    baseUrl,
    `/rest/api/3/issue/${feature.ticketId}/comment?orderBy=created`
  );

  return data.comments.map((c) => {
    const bodyText = adfToPlainText(c.body);
    const match = bodyText.match(META_RE);
    return {
      id: c.id,
      author: c.author?.displayName ?? "unknown",
      createdAt: c.created,
      body: bodyText,
      url: `${baseUrl}/browse/${feature.ticketId}?focusedCommentId=${c.id}`,
      meta: match
        ? { agent: match[1], stage: match[2], status: match[3], timestamp: match[4] }
        : null,
    };
  });
}

// Jira Cloud comment bodies are Atlassian Document Format (ADF), not plain
// Markdown — flatten text nodes so the meta-line regex (and human display)
// can work as if it were a plain string.
function adfToPlainText(node) {
  if (!node) return "";
  if (typeof node === "string") return node;
  if (node.type === "text") return node.text ?? "";
  if (Array.isArray(node.content)) {
    return node.content.map(adfToPlainText).join(node.type === "paragraph" ? "\n" : "");
  }
  return "";
}
