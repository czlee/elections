import { resolve } from '$app/paths';

/** A site path ("/party-vote/") with the base path prepended (relative during prerendering). */
export const link = (/** @type {string} */ path) => resolve(/** @type {any} */ (path.slice(1)));
