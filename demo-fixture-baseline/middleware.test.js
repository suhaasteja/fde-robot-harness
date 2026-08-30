import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { authorize } from "./middleware.js";

test("untrusted middleware header cannot bypass authorization", () => {
  const result = authorize({
    headers: { "x-middleware-subrequest": "middleware:middleware" },
    session: null,
  });
  assert.equal(result.allowed, false);
});

test("authenticated administrators remain authorized", () => {
  const result = authorize({ headers: {}, session: { role: "admin" } });
  assert.equal(result.allowed, true);
});

test("Next.js dependency is patched for CVE-2026-45109", () => {
  const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));
  assert.equal(pkg.dependencies.next, "15.5.18");
});
