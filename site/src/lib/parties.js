// Party colours, validated with the dataviz palette validator in House order
// (TPM, Green, Labour, TOP, NZ First, National, ACT), which is the order they
// sit next to each other in the parliament chart. NZ First's conventional
// black is kept as a warm neutral: it fails the chroma floor by design and is
// always direct-labelled. Colours are CSS variables (see app.css) so that
// dark mode gets its own steps.

/** Parties in House order, left to right. */
export const HOUSE_ORDER = ['te-pati-maori', 'green', 'labour', 'top', 'nz-first', 'national', 'act'];

/** @param {string | null | undefined} party */
export const colour = (party) =>
	party && HOUSE_ORDER.includes(party) ? `var(--party-${party})` : 'var(--party-other)';
