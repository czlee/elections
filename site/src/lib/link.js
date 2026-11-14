import { resolve } from '$app/paths';
import { page } from '$app/state';
import { baseOf, prefix } from '#lib/bases.js';

/**
 * A site path ("/party-vote/") with the base path prepended (relative during
 * prerendering), under the current page's base year unless `base` is given.
 * Call it while rendering, since it reads the current page.
 */
export const link = (/** @type {string} */ path, /** @type {string | undefined} */ base = undefined) =>
	resolve(/** @type {any} */ ((prefix(base ?? baseOf(page.params.base)) + path).slice(1)));
