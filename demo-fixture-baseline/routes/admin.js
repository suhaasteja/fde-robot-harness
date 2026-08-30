import { authorize } from "../middleware.js";
import { loadSession } from "../lib/session.js";
import { record } from "../lib/audit.js";

// The privileged surface. Everything here is gated by authorize(), which is why
// a middleware bypass is critical rather than merely bad: it reaches refunds and
// user deletion, not just a read endpoint.
export function refund(request) {
  const decision = authorize(request);
  if (!decision.allowed) return { status: 403, body: "forbidden" };
  const session = loadSession(request.cookies?.session);
  record("admin.refund", session, { order: request.body?.order });
  return { status: 200, body: "refunded" };
}

export function deleteUser(request) {
  const decision = authorize(request);
  if (!decision.allowed) return { status: 403, body: "forbidden" };
  const session = loadSession(request.cookies?.session);
  record("admin.deleteUser", session, { target: request.body?.user });
  return { status: 200, body: "deleted" };
}
