export function authorize(request) {
  return { allowed: request.session?.role === "admin" };
}
