// GitHub adapter: normalizes GitHub Issues + Projects v2 board state into the
// shared feature shape the dashboard's routes/frontend consume, so nothing
// above this file needs to know GitHub's data model.
//
// Auth: GITHUB_TOKEN env var (a PAT with `repo` + `read:project` scope, or
// `gh auth token` output).

const GITHUB_API = "https://api.github.com";
const GITHUB_GRAPHQL = "https://api.github.com/graphql";

const STAGE_FIELD = "Stage";
const SLUG_FIELD = "Feature Slug";
const AGENT_FIELD = "Current Agent";
const BRANCH_FIELD = "Feature Branch";

// <!-- meta: agent=<agent> stage=<stage> status=<status> timestamp=<ISO> -->
const META_RE = /<!--\s*meta:\s*agent=(\S+)\s+stage=(\S+)\s+status=(\S+)\s+timestamp=(\S+)\s*-->/;

function requireToken() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error(
      "GITHUB_TOKEN environment variable is not set. Set it to a personal " +
        "access token (or `gh auth token` output) with repo + read:project scope."
    );
  }
  return token;
}

async function githubRequest(url, { method = "GET", body } = {}) {
  const token = requireToken();
  const res = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GitHub API ${method} ${url} failed: ${res.status} ${text}`);
  }
  return res.json();
}

async function graphql(query, variables) {
  const json = await githubRequest(GITHUB_GRAPHQL, {
    method: "POST",
    body: { query, variables },
  });
  if (json.errors?.length) {
    throw new Error(`GitHub GraphQL error: ${json.errors.map((e) => e.message).join("; ")}`);
  }
  return json.data;
}

const PROJECT_ITEMS_QUERY = /* GraphQL */ `
  query ($owner: String!, $number: Int!, $after: String) {
    user(login: $owner) {
      projectV2(number: $number) {
        items(first: 50, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            content {
              ... on Issue {
                number
                title
                url
                updatedAt
              }
            }
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldTextValue {
                  text
                  field {
                    ... on ProjectV2FieldCommon {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
`;

function fieldValue(fieldValues, fieldName) {
  const node = fieldValues.nodes.find((n) => n.field?.name === fieldName);
  if (!node) return null;
  return node.name ?? node.text ?? null;
}

/**
 * Lists every feature currently on the Projects v2 board, normalized to:
 * { slug, title, stage, currentAgent, branch, ticketId, ticketUrl, updatedAt }
 */
export async function listFeatures(config) {
  const { projectOwner, projectNumber } = config.github;
  if (!projectOwner || !projectNumber) {
    throw new Error(
      "GitHub project owner/number could not be resolved (expected " +
        "PROJECT_OWNER/PROJECT_NUMBER in github-workflow.instructions.md, set " +
        "after running .orchestrator/scripts/setup-github-project.sh)."
    );
  }

  const features = [];
  let after = null;
  for (;;) {
    const data = await graphql(PROJECT_ITEMS_QUERY, {
      owner: projectOwner,
      number: projectNumber,
      after,
    });
    const project = data?.user?.projectV2;
    if (!project) {
      throw new Error(
        `Projects v2 board not found for user "${projectOwner}", number ${projectNumber}.`
      );
    }
    for (const item of project.items.nodes) {
      const issue = item.content;
      if (!issue) continue; // draft items with no linked issue
      const slug = fieldValue(item.fieldValues, SLUG_FIELD);
      features.push({
        slug: slug ?? `issue-${issue.number}`,
        title: issue.title,
        stage: fieldValue(item.fieldValues, STAGE_FIELD) ?? "Backlog",
        currentAgent: fieldValue(item.fieldValues, AGENT_FIELD),
        branch: fieldValue(item.fieldValues, BRANCH_FIELD),
        ticketId: String(issue.number),
        ticketUrl: issue.url,
        updatedAt: issue.updatedAt,
      });
    }
    if (!project.items.pageInfo.hasNextPage) break;
    after = project.items.pageInfo.endCursor;
  }
  return features;
}

/**
 * Fetches and parses the comment activity feed for one feature's issue,
 * extracting the `<!-- meta: ... -->` convention documented in
 * .orchestrator/skills/ticket-comments.skill.md.
 */
export async function getFeatureComments(config, slug) {
  const features = await listFeatures(config);
  const feature = features.find((f) => f.slug === slug);
  if (!feature) {
    throw new Error(`No GitHub issue found on the board for feature slug "${slug}".`);
  }

  const { owner, repo } = config.github;
  const comments = await githubRequest(
    `${GITHUB_API}/repos/${owner}/${repo}/issues/${feature.ticketId}/comments?per_page=100`
  );

  return comments.map((c) => {
    const match = c.body?.match(META_RE);
    return {
      id: String(c.id),
      author: c.user?.login ?? "unknown",
      createdAt: c.created_at,
      body: c.body ?? "",
      url: c.html_url,
      meta: match
        ? { agent: match[1], stage: match[2], status: match[3], timestamp: match[4] }
        : null,
    };
  });
}
