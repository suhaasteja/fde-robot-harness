import { loadSession } from "../lib/session.js";
import { allow } from "../lib/rates.js";
import { record } from "../lib/audit.js";

export function listOrders(request) {
  const session = loadSession(request.cookies?.session);
  if (!allow(session.user ?? "anon")) return { status: 429, body: "slow down" };
  if (session.role === "guest") return { status: 401, body: "sign in" };
  record("orders.list", session);
  return { status: 200, body: [{ id: "ord_1001", total: 4200 }] };
}
