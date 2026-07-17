import { test } from "node:test";
import assert from "node:assert/strict";
import * as jiraAdapter from "../adapters/jira.js";

const config = {
  provider: "jira",
  jira: {
    baseUrl: "https://acme.atlassian.net",
    projectKey: "PROJ",
  },
};

function withMockedFetch(t, handler) {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    calls.push({ url: String(url), init });
    return handler(String(url), init);
  });
  return calls;
}

function jsonResponse(body, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}

test("getFeatureComments resolves an issue-key-shaped slug directly (no project search)", async (t) => {
  process.env.JIRA_EMAIL = "bot@acme.test";
  process.env.JIRA_API_TOKEN = "test-token";
  t.after(() => {
    delete process.env.JIRA_EMAIL;
    delete process.env.JIRA_API_TOKEN;
  });

  const calls = withMockedFetch(t, (url) => {
    // Only the single-issue comments endpoint should be hit — the JQL
    // /search endpoint (a full project scan) must not be called when the
    // slug already is the issue key (the default, no custom slug field).
    assert.ok(!url.includes("/search"), `unexpected project search for URL: ${url}`);
    assert.ok(url.includes("/rest/api/3/issue/PROJ-42/comment"));
    return jsonResponse({ comments: [] });
  });

  const comments = await jiraAdapter.getFeatureComments(config, "PROJ-42");

  assert.deepEqual(comments, []);
  assert.equal(calls.length, 1);
});

test("getFeatureComments falls back to a full project search for a genuinely custom slug", async (t) => {
  process.env.JIRA_EMAIL = "bot@acme.test";
  process.env.JIRA_API_TOKEN = "test-token";
  process.env.JIRA_FEATURE_SLUG_FIELD = "customfield_999";
  t.after(() => {
    delete process.env.JIRA_EMAIL;
    delete process.env.JIRA_API_TOKEN;
    delete process.env.JIRA_FEATURE_SLUG_FIELD;
  });

  withMockedFetch(t, (url) => {
    if (url.includes("/search")) {
      return jsonResponse({
        total: 1,
        issues: [
          {
            key: "PROJ-9",
            fields: {
              summary: "Some feature",
              status: { name: "Implementation" },
              labels: [],
              updated: "",
              customfield_999: "custom-slug",
            },
          },
        ],
      });
    }
    assert.ok(url.includes("/rest/api/3/issue/PROJ-9/comment"));
    return jsonResponse({ comments: [] });
  });

  const comments = await jiraAdapter.getFeatureComments(config, "custom-slug");
  assert.deepEqual(comments, []);
});
