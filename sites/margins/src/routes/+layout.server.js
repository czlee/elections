import { SITE_NAME, SITE_ORIGIN, CARD, pageMeta } from '#lib/server/og.js';

export function load({ params, url }) {
	const { title, description, version } = pageMeta(params.election);
	// url.pathname includes the base path while prerendering; each page's card is its og.png.
	const pageUrl = SITE_ORIGIN + url.pathname;
	return {
		meta: {
			siteName: SITE_NAME, title, description, url: pageUrl,
			image: `${pageUrl}og.png?v=${version}`, imageWidth: CARD.width, imageHeight: CARD.height
		}
	};
}
