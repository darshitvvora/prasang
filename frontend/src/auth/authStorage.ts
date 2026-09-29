// Persists the session token. In mock mode this is a Mockoon token; in
// supabase mode supabase-js owns the session and this store is unused.
const KEY = 'prasang.token';

export interface TokenStore {
  get(): string | null;
  set(token: string): void;
  clear(): void;
}

export function createTokenStore(storage: Storage): TokenStore {
  return {
    get: () => storage.getItem(KEY),
    set: (token) => storage.setItem(KEY, token),
    clear: () => storage.removeItem(KEY),
  };
}
