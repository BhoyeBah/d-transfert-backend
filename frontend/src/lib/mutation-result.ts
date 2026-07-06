export type MutationResult<T = undefined> =
  | { ok: true; data: T }
  | { ok: false; message: string };
