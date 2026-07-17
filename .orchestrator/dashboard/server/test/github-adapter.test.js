import { test } from "node:test";
import assert from "node:assert/strict";
import * as githubAdapter from "../adapters/github.js";

const config = {
  provider: "github",
  github: {
    owner: "acme",
    repo: "widgets",
    issueLabels: [],
    projectOwner: "acme",
    projectNumber: 1,
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

test("getFeatureComments resolves a fallback-shaped slug straight to an issue number (no board scan)", async (t) => {
  process.env.GITHUB_TOKEN = "test-token";
  t.after(() => delete process.env.GITHUB_TOKEN);

  const calls = withMockedFetch(t, (url) => {
    // Only the REST comments endpoint should ever be hit — the GraphQL
    // project-board endpoint must not be called for a slug shaped like the
    // default "issue-<number>" fallback, since the issue number is already
    // right there in the slug.
    assert.ok(!url.includes("/graphql"), `unexpected GraphQL call for URL: ${url}`);
    assert.ok(url.includes("/repos/acme/widgets/issues/42/comments"));
    return jsonResponse([]);
  });

  const comments = await githubAdapter.getFeatureComments(config, "issue-42");

  assert.deepEqual(comments, []);
  assert.equal(calls.length, 1);
});

test("getFeatureComments falls back to a full board scan for a genuinely custom slug", async (t) => {
  process.env.GITHUB_TOKEN = "test-token";
  t.after(() => delete process.env.GITHUB_TOKEN);

  withMockedFetch(t, (url) => {
    if (url.includes("/graphql")) {
      return jsonResponse({
        data: {
          user: {
            projectV2: {
              items: {
                pageInfo: { hasNextPage: false, endCursor: null },
                nodes: [
                  {
                    content: { number: 7, title: "Some feature", url: "https://x/7", updatedAt: "" },
                    fieldValues: {
                      nodes: [
                        { name: "custom-slug", field: { name: "Feature Slug" } },
                        { name: "Implementation", field: { name: "Stage" } },
                      ],
                    },
                  },
                ],
              },
            },
          },
        },
      });
    }
    assert.ok(url.includes("/repos/acme/widgets/issues/7/comments"));
    return jsonResponse([]);
  });

  const comments = await githubAdapter.getFeatureComments(config, "custom-slug");
  assert.deepEqual(comments, []);
});
