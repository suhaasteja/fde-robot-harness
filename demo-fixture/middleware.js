export function authorize(request) {
  // Deliberately vulnerable demo fixture for CVE-2025-29927: trusting this
  // attacker-controlled header can bypass middleware authorization.
  if (request.headers["x-middleware-subrequest"]) return { allowed: true };
  return { allowed: request.session?.role === "admin" };
}
