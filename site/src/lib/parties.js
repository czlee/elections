// Party colours, validated with the dataviz palette validator in the order
// they sit next to each other round the horseshoe chart (Labour, Green, TPM,
// TOP, NZ First, ACT, National). NZ First is charcoal (light grey in dark
// mode): a neutral, so it fails the lightness band and chroma floor by design
// and is always labelled; in dark mode it's in the CVD warning band against
// TOP. ACT is pink. Colours are CSS variables (see app.css) so that dark mode
// gets its own steps.

/** Parties in horseshoe order, left to right. */
export const HOUSE_ORDER = ['labour', 'green', 'te-pati-maori', 'top', 'nz-first', 'act', 'national'];

/** @param {string | null | undefined} party */
export const colour = (party) =>
	party && HOUSE_ORDER.includes(party) ? `var(--party-${party})` : 'var(--party-other)';
