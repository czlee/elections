// Base years: the past election whose special votes are applied to 2026. The
// default lives at the site root (/party-vote/, ...); the others under their
// year (/2020/party-vote/, ...). Each has its own data in src/lib/data/<base>/.

export const DEFAULT_BASE = '2023';
/** Newest first, as the site lists them. */
export const BASES = ['2023', '2020', '2017'];
export const OTHER_BASES = BASES.filter((b) => b !== DEFAULT_BASE);

/** Why a base year has no electorate projections, completing "because …". */
export const NO_ELECTORATES_REASON = /** @type {Record<string, string>} */ ({
	'2020':
		'the Wayback Machine doesn’t have the 2020 preliminary results by electorate (only the national totals)'
});

/** The base year for a route's (optional) base param. */
export const baseOf = (/** @type {string | undefined} */ param) => param ?? DEFAULT_BASE;

/** The path prefix for a base year: "" for the default, "/2020" otherwise. */
export const prefix = (/** @type {string} */ base) => (base === DEFAULT_BASE ? '' : `/${base}`);
