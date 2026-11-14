import { BASES, baseOf } from '#lib/bases.js';
import { electorateBases, national } from '#lib/server/data.js';
import { SITE_NAME, SITE_ORIGIN, CARD, pageMeta } from '#lib/server/og.js';

export function load({ params, route, url }) {
	const base = baseOf(/** @type {any} */ (params).base);
	const { title, description, version } = pageMeta(route.id, base, /** @type {any} */ (params).slug);
	// url.pathname includes the base path while prerendering; each page's card is its og.png.
	const pageUrl = SITE_ORIGIN + url.pathname;
	return {
		base,
		hasElectorates: national(base).has_electorates,
		/** Every base year, for the switcher. */
		bases: BASES.map((b) => ({ base: b, hasElectorates: electorateBases.includes(b) })),
		meta: {
			siteName: SITE_NAME, title, description, url: pageUrl,
			image: `${pageUrl}og.png?v=${version}`, imageWidth: CARD.width, imageHeight: CARD.height
		}
	};
}
