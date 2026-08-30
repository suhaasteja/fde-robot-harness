export function authorize(request) {
  // External clients can set x-middleware-subrequest, so never trust it for
  // authorization decisions; rely only on the authenticated session role.
  return { allowed: request.session?.role === "admin" };
}
