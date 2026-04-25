export function trimStringValues<T extends object>(obj: T): T {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => [k, typeof v === "string" ? v.trim() : v]),
  ) as T;
}