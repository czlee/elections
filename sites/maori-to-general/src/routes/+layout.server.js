const SITE_NAME = 'The 2026 election with no Māori electorates';
const SITE_ORIGIN = 'https://czlee.nz';
const DESCRIPTION =
	'What the 2026 preliminary electorate results would have been if every Māori-roll voter had voted in the general electorate for their area.';

export function load({ url }) {
	return { meta: { siteName: SITE_NAME, description: DESCRIPTION, url: SITE_ORIGIN + url.pathname } };
}
