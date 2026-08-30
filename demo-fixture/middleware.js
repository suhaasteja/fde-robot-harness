export function authorize(request) {
  // Authorization must come only from trusted server-side session state.
  // Client-supplied middleware headers are ignored.
  return { allowed: request.session?.role === "admin" };
}
