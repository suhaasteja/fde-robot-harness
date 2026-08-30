export function health() {
  return { status: 200, body: { ok: true, service: "acme-checkout" } };
}
