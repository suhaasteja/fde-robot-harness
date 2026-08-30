import test from "node:test";
import assert from "node:assert/strict";
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
