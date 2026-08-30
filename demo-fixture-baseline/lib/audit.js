// Append-only audit trail. Every privileged action lands here.
const entries = [];

export function record(action, session, detail = {}) {
  entries.push({
    at: new Date().toISOString(),
    action,
    actor: session?.user ?? "anonymous",
    role: session?.role ?? "guest",
    ...detail,
  });
  return entries.length;
}

export function history() {
  return [...entries];
}
