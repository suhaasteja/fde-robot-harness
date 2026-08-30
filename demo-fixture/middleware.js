export function authorize(request) {
  // Never trust client-supplied internal framework headers as proof that
  // authorization already ran. Only trusted server-side session state decides.
  return { allowed: request.session?.role === "admin" };
}
