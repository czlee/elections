import { resolve } from '$app/paths';

/** A site path ("/national/") with the base path prepended (relative during prerendering). */
export const link = (/** @type {string} */ path) => resolve(/** @type {any} */ (path.slice(1)));
