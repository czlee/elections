import { resolve } from '$app/paths';

/**
 * A site path ("/electorates/") with the base path prepended (relative
 * during prerendering). Call it while rendering.
 */
export const link = (/** @type {string} */ path) => resolve(/** @type {any} */ (path.slice(1)));
