import { useSyncExternalStore } from "react";

const noop = () => () => {};

/**
 * false on the server and during hydration, true afterwards. Use it to keep the first
 * client render identical to the server HTML when output depends on client-only data.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}
