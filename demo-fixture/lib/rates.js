// Naive fixed-window rate limiter, keyed per actor.
const WINDOW_MS = 60_000;
const LIMIT = 30;
const hits = new Map();

export function allow(key, now = Date.now()) {
  const bucket = hits.get(key)?.filter((t) => now - t < WINDOW_MS) ?? [];
  bucket.push(now);
  hits.set(key, bucket);
  return bucket.length <= LIMIT;
}
