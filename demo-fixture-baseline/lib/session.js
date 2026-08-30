// Server-side session lookup. The only trustworthy source of identity:
// everything here is derived from the signed session cookie, never from
// request headers a client can set.
const SESSIONS = new Map([
  ["sess_admin", { user: "aahan", role: "admin" }],
  ["sess_staff", { user: "suhaas", role: "staff" }],
  ["sess_guest", { user: null, role: "guest" }],
]);

export function loadSession(cookie) {
  if (!cookie) return { user: null, role: "guest" };
  return SESSIONS.get(cookie) ?? { user: null, role: "guest" };
}

export function isAdmin(session) {
  return session?.role === "admin";
}
