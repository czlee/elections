// Social preview metadata (titles, descriptions) and the 1200×630 PNG cards
// that og:image points to. Each page's card is prerendered by an og.png
// endpoint next to it; the page's meta and its card come from the same
// cardData(), so the description and the image always agree, and the image
// URL carries a hash of that data and of the code that draws the card, so
// social platforms refetch it when the numbers or the design change.
// Adapted from the 2026-projection site's og.js.
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inflateSync } from 'node:zlib';
import { render } from 'svelte/server';
import { Resvg } from '@resvg/resvg-js';
import Parliament from '#lib/components/Parliament.svelte';
import { HOUSE_ORDER } from '#lib/parties.js';
import { votes, points, candidateName } from '#lib/format.js';
import { national, summaries } from '#lib/server/data.js';
import appCss from '../../app.css?raw';
import ogSource from './og.js?raw';
import parliamentSource from '#lib/components/Parliament.svelte?raw';

export const SITE_NAME = 'The 2026 election if there were no Māori electorates';
/** Where the site is served; og:url and og:image must be absolute. */
export const SITE_ORIGIN = 'https://czlee.nz';
export const CARD = { width: 1200, height: 630 };

const NUMBERS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
const listing = (/** @type {string[]} */ xs) =>
	xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`;
const minus = (/** @type {number} */ n) => (n > 0 ? `+${n}` : `−${-n}`);
const cap = (/** @type {string} */ s) => s[0].toUpperCase() + s.slice(1);
const names = Object.fromEntries(national.parties.map((/** @type {any} */ p) => [p.id, p.short]));
const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'Independent');

/** Everything the home card (and the home-ish pages' descriptions) shows. */
function homeData() {
	const n = national;
	const ids = n.parties.map((/** @type {any} */ p) => p.id).filter((/** @type {string} */ id) =>
		n.seats.counted[id]?.total || n.seats.none[id]?.total);
	const total = (/** @type {'counted' | 'none'} */ v, /** @type {string} */ id) => n.seats[v][id]?.total ?? 0;
	const changes = ids
		.map((/** @type {string} */ id) => ({ id, name: names[id], change: total('none', id) - total('counted', id) }))
		.filter((/** @type {any} */ c) => c.change)
		.sort((/** @type {any} */ a, /** @type {any} */ b) =>
			Number(b.change > 0) - Number(a.change > 0) || (a.change > 0 ? b.change - a.change : a.change - b.change));
	const flips = summaries().filter((e) => e.flips)
		.map((e) => ({ name: e.name, from: party(e.prelim_winner_party), to: party(e.winner_party) }));
	const seats = (/** @type {'counted' | 'none'} */ v) => Object.fromEntries(ids.map((/** @type {string} */ id) =>
		[id, { total: total(v, id), electorate: n.seats[v][id]?.electorate ?? 0 }]));
	return {
		kind: 'home', changes, flips, house: n.house, general: n.general_electorates,
		labourGain: (n.seats.none.labour?.electorate ?? 0) - (n.seats.counted.labour?.electorate ?? 0),
		names: Object.fromEntries(ids.map((/** @type {string} */ id) => [id, names[id]])),
		seats: seats('none'), compare: seats('counted')
	};
}

/** "7 of the 64 general electorates would flip from National to Labour…" plus the seat changes. */
function homeSummary(/** @type {ReturnType<typeof homeData>} */ d) {
	const gains = d.changes.filter((c) => c.change > 0), losses = d.changes.filter((c) => c.change < 0);
	const fmt = (/** @type {any[]} */ cs) => cs.map((c) => `${c.name} ${minus(c.change)}`).join(', ');
	const from = new Set(d.flips.map((f) => f.from)), to = new Set(d.flips.map((f) => f.to));
	const dir = from.size === 1 && to.size === 1 ? ` from ${[...from][0]} to ${[...to][0]}` : '';
	const gain = d.labourGain > 0 ? `, for a net gain of ${d.labourGain} for Labour` : '';
	const seats = d.changes.length ? ` Overall seats: ${[fmt(gains), fmt(losses)].filter(Boolean).join('; ')}.` : '';
	return `${d.flips.length} of the ${d.general} general electorates would flip${dir}${gain}.${seats}`;
}

/** Everything an electorate card (and its page description) shows. */
function electorateData(/** @type {string} */ slug) {
	const e = summaries().find((x) => x.slug === slug);
	if (!e) return null;
	const who = (/** @type {string} */ name, /** @type {string | null} */ id) => ({ name: candidateName(name), party: party(id), id });
	return {
		kind: 'electorate', name: e.name, flips: e.flips,
		counted: { leader: who(e.prelim_winner, e.prelim_winner_party), second: who(e.prelim_second, e.prelim_second_party),
			margin: e.prelim_margin, pct: e.prelim_margin_pct },
		none: { leader: who(e.winner, e.winner_party), second: who(e.second, e.second_party), margin: e.margin, pct: e.margin_pct }
	};
}

function electorateSummary(/** @type {NonNullable<ReturnType<typeof electorateData>>} */ d) {
	const { counted: a, none: b } = d;
	const lead = `${b.leader.name} would win by ${votes(b.margin)} votes (${points(b.pct)}) over ${b.second.name}`;
	return d.flips
		? `Would flip from ${a.leader.party} to ${b.leader.party} if there were no Māori electorates: ${lead}, after ${a.leader.name} led by ${votes(a.margin)} in the preliminary count.`
		: `${b.leader.party} would hold if there were no Māori electorates: ${lead}, against a lead of ${votes(a.margin)} in the preliminary count.`;
}

/** The card for a route: the home card for every page but an electorate's. */
export function cardData(/** @type {string | null} */ routeId, /** @type {string | undefined} */ slug) {
	return (routeId === '/electorate/[slug]' && slug && electorateData(slug)) || homeData();
}

/** Everything that draws a card, so a design change gives it a new URL too. */
const LAYOUT = ogSource + parliamentSource + appCss;

/** Title, description and image version for a page. */
export function pageMeta(/** @type {string | null} */ routeId, /** @type {string | undefined} */ slug) {
	const data = cardData(routeId, slug);
	const version = createHash('sha1').update(JSON.stringify(data)).update(LAYOUT).digest('hex').slice(0, 10);
	/** @type {{title: string, description: string}} */
	let m;
	if (data.kind === 'electorate') {
		const d = /** @type {NonNullable<ReturnType<typeof electorateData>>} */ (data);
		m = { title: `${d.name} · ${SITE_NAME}`, description: electorateSummary(d) };
	} else {
		const d = /** @type {ReturnType<typeof homeData>} */ (data);
		if (routeId === '/electorates') {
			const f = d.flips;
			m = {
				title: `Electorates · ${SITE_NAME}`,
				description: `All ${d.general} general electorates with the Māori-roll votes added. ${
					f.length ? `${cap(NUMBERS[f.length] ?? String(f.length))} would flip: ${listing(f.map((x) => x.name))}.` : 'None would flip.'}`
			};
		} else {
			m = { title: SITE_NAME, description: `${homeSummary(d)} Based on the 2026 preliminary count.` };
		}
	}
	return { ...m, version };
}

// ---------------------------------------------------------------------------
// Rendering

/** Light-theme colour tokens from app.css's first :root block. */
const TOKENS = Object.fromEntries(
	[...(appCss.match(/:root\s*\{([^}]*)\}/)?.[1] ?? '').matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{3,8})/g)].map((m) => [m[1], m[2]])
);
const T = (/** @type {string} */ name) => TOKENS[name] ?? '#000';
const partyColour = (/** @type {string | null | undefined} */ id) =>
	T(id && HOUSE_ORDER.includes(id) ? `party-${id}` : 'party-other');

/**
 * resvg reads TTF/OTF, not WOFF, so unwrap Fontsource's WOFF 1.0 files into
 * plain sfnt: the same tables, each zlib-inflated if it was compressed.
 */
function woffToSfnt(/** @type {Buffer} */ woff) {
	if (woff.readUInt32BE(0) !== 0x774f4646) throw new Error('not a WOFF 1.0 file');
	const flavor = woff.readUInt32BE(4), numTables = woff.readUInt16BE(12);
	const tables = [];
	for (let i = 0; i < numTables; i++) {
		const o = 44 + 20 * i;
		const [offset, compLength, origLength] = [woff.readUInt32BE(o + 4), woff.readUInt32BE(o + 8), woff.readUInt32BE(o + 12)];
		const raw = woff.subarray(offset, offset + compLength);
		tables.push({ tag: woff.readUInt32BE(o), checksum: woff.readUInt32BE(o + 16),
			data: compLength < origLength ? inflateSync(raw) : raw });
	}
	let entrySelector = 0;
	while (2 ** (entrySelector + 1) <= numTables) entrySelector++;
	const header = Buffer.alloc(12 + 16 * numTables);
	header.writeUInt32BE(flavor, 0);
	header.writeUInt16BE(numTables, 4);
	header.writeUInt16BE(16 * 2 ** entrySelector, 6);
	header.writeUInt16BE(entrySelector, 8);
	header.writeUInt16BE(16 * numTables - 16 * 2 ** entrySelector, 10);
	/** @type {Uint8Array[]} */
	const chunks = [header];
	let offset = header.length;
	tables.forEach((t, i) => {
		const o = 12 + 16 * i;
		header.writeUInt32BE(t.tag, o);
		header.writeUInt32BE(t.checksum, o + 4);
		header.writeUInt32BE(offset, o + 8);
		header.writeUInt32BE(t.data.length, o + 12);
		const pad = (4 - (t.data.length % 4)) % 4;
		chunks.push(t.data, Buffer.alloc(pad));
		offset += t.data.length + pad;
	});
	return Buffer.concat(chunks);
}

/** @type {string[] | undefined} */
let fonts;
/**
 * DM Sans as TTF files in a temporary directory. (resvg-js's Node build
 * ignores `fontBuffers`, and then loads the system fonts, so it gets paths.)
 */
function loadFonts() {
	if (fonts) return fonts;
	// Builds run from the site's directory, where node_modules is.
	const src = `${process.cwd()}/node_modules/@fontsource/dm-sans/files`;
	const dir = mkdtempSync(join(tmpdir(), 'og-fonts-'));
	return (fonts = ['latin', 'latin-ext'].flatMap((subset) => [400, 600, 700].map((w) => {
		const file = join(dir, `dm-sans-${subset}-${w}.ttf`);
		writeFileSync(file, woffToSfnt(readFileSync(`${src}/dm-sans-${subset}-${w}-normal.woff`)));
		return file;
	})));
}

const esc = (/** @type {string} */ s) =>
	s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** A text element. */
function text(/** @type {number} */ x, /** @type {number} */ y, /** @type {string} */ s,
	{ size = 28, weight = 400, fill = T('text'), anchor = 'start', spacing = 0 } = {}) {
	return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}"${
		spacing ? ` letter-spacing="${spacing}"` : ''}>${esc(s)}</text>`;
}

/** The rendered width of a line of text, measured by resvg with the card's font. */
function textWidth(/** @type {string} */ s, /** @type {number} */ size, /** @type {number} */ weight) {
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="100" font-family="DM Sans">` +
		text(0, 60, s, { size, weight }) + '</svg>';
	const box = new Resvg(svg, { font: { fontFiles: loadFonts(), loadSystemFonts: false, defaultFontFamily: 'DM Sans' } }).getBBox();
	return box ? box.width : s.length * 0.55 * size;
}

/** Shrinks a font size so roughly `chars` characters fit in `width` (DM Sans averages ~0.55em, less for lower case). */
const fit = (/** @type {string} */ s, /** @type {number} */ size, /** @type {number} */ width, em = 0.55) =>
	Math.min(size, Math.floor(width / (em * s.length)));
/** "would win by 140 (0.34 pp)", for an electorate card panel. */
const margin = (/** @type {string} */ verb, /** @type {any} */ r) => `${verb} by ${votes(r.margin)} (${points(r.pct)})`;

/** The site's horseshoe chart, as a standalone SVG fragment with literal colours. */
function horseshoe(/** @type {ReturnType<typeof homeData>} */ d) {
	const house = d.house.none;
	const { body } = render(Parliament, {
		props: { seats: d.seats, names: d.names, compare: d.compare, majority: Math.floor(house / 2) + 1, overhang: house - 120 }
	});
	const svg = body.match(/<svg[\s\S]*?<\/svg>/)?.[0];
	if (!svg) throw new Error('no <svg> in Parliament output');
	const style = `<style>
		.hs .halo { fill: none; stroke: ${T('text')}; stroke-width: 1.3; }
		.hs .majority { stroke: ${T('text-3')}; stroke-dasharray: 3 3; }
		.hs text { font-size: 10px; fill: ${T('text-2')}; }
		.hs .maj { font-size: 11px; font-weight: 600; fill: ${T('text')}; }
	</style>`;
	return svg
		.replace(/<!--[\s\S]*?-->/g, '')
		.replace(/var\(--([\w-]+)\)/g, (_, name) => T(name))
		.replace(/>/, `>${style}`);
}

const kicker = (/** @type {string} */ s, y = 92) =>
	text(72, y, s.toUpperCase(), { size: 22, weight: 600, fill: T('text-3'), spacing: 2 });
const footer = () =>
	text(72, 572, 'czlee.nz/elections/maori-to-general', { size: 24, weight: 600, fill: T('text-2') }) +
	text(1128, 572, 'Preliminary count · not an official result', { size: 22, fill: T('text-3'), anchor: 'end' });

function homeSvg(/** @type {ReturnType<typeof homeData>} */ d) {
	const out = [kicker('New Zealand general election', 82)];
	out.push(text(72, 150, '2026 election if there', { size: 48, weight: 700 }));
	out.push(text(72, 208, 'were no Māori electorates', { size: 48, weight: 700 }));
	const headline = `${d.flips.length} of ${d.general} electorates would flip`;
	out.push(text(72, 296, headline, { size: fit(headline, 44, 620, 0.5), weight: 700, fill: T('accent') }));
	const from = new Set(d.flips.map((f) => f.from)), to = new Set(d.flips.map((f) => f.to));
	let y = 296;
	if (from.size === 1 && to.size === 1) {
		y += 40;
		out.push(text(72, y, `${[...from][0]} to ${[...to][0]}`, { size: 28, fill: T('text-2') }));
	}
	y += 62;
	const changes = d.changes.slice(0, 4);
	changes.forEach((c, i) => {
		const cy = y + i * 42;
		out.push(`<circle cx="86" cy="${cy - 10}" r="10" fill="${partyColour(c.id)}"/>`);
		out.push(text(112, cy, c.name, { size: 32, weight: 600 }));
		out.push(text(420, cy, minus(c.change), { size: 32, weight: 700, anchor: 'end' }));
	});
	y += Math.max(0, changes.length - 1) * 42 + 52;
	if (d.house.counted !== d.house.none) {
		out.push(text(72, y, `House: ${d.house.counted} to ${d.house.none} seats`, { size: 26, fill: T('text-2') }));
	}
	out.push(`<svg class="hs" x="660" y="56" width="480" height="440">${horseshoe(d)}</svg>`);
	out.push(text(900, 530, 'Seats with no Māori electorates · filled: electorate, ring: list', { size: 20, fill: T('text-3'), anchor: 'middle' }));
	out.push(footer());
	return out.join('');
}

function electorateSvg(/** @type {NonNullable<ReturnType<typeof electorateData>>} */ d) {
	const out = [kicker('2026 election · if there were no Māori electorates · general electorate')];
	out.push(text(72, 180, d.name, { size: fit(d.name, 80, 1056), weight: 700 }));
	const { counted: a, none: b } = d;
	const badge = d.flips ? `Would flip from ${a.leader.party} to ${b.leader.party}` : `${b.leader.party} would hold`;
	const bw = Math.ceil(textWidth(badge, 28, 600)) + 48;
	out.push(`<rect x="72" y="214" width="${bw}" height="50" rx="25" fill="${d.flips ? partyColour(b.leader.id) : T('surface-2')}"/>`);
	out.push(text(96, 248, badge, { size: 28, weight: 600, fill: d.flips ? '#ffffff' : T('text') }));
	const panel = (/** @type {number} */ x, /** @type {string} */ label, /** @type {any} */ r, /** @type {string} */ verb, strong = false) => [
		`<rect x="${x}" y="300" width="500" height="210" rx="14" fill="${strong ? '#ffffff' : T('surface-2')}" stroke="${T('border')}"/>`,
		`<rect x="${x}" y="300" width="10" height="210" rx="5" fill="${partyColour(r.leader.id)}"/>`,
		text(x + 36, 348, label.toUpperCase(), { size: fit(label, 20, 440, 0.66), weight: 600, fill: T('text-3'), spacing: 1.5 }),
		text(x + 36, 400, r.leader.name, { size: fit(r.leader.name, 40, 440), weight: 700 }),
		text(x + 36, 442, r.leader.party, { size: 28, weight: 600, fill: partyColour(r.leader.id) === T('party-other') ? T('text-2') : partyColour(r.leader.id) }),
		text(x + 36, 486, margin(verb, r), { size: fit(margin(verb, r), 28, 440, 0.46), fill: T('text-2') })
	].join('');
	out.push(panel(72, 'As counted', a, 'leads'));
	out.push(`<path d="M586 405h22m-9-10l10 10-10 10" fill="none" stroke="${T('text-3')}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`);
	out.push(panel(628, 'If there were no Māori electorates', b, 'would win', true));
	out.push(footer());
	return out.join('');
}

/** The card as SVG markup. */
export function cardSvg(/** @type {ReturnType<typeof cardData>} */ d) {
	const inner = d.kind === 'electorate' ? electorateSvg(/** @type {any} */ (d)) : homeSvg(/** @type {any} */ (d));
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD.width}" height="${CARD.height}" viewBox="0 0 ${CARD.width} ${CARD.height}" font-family="DM Sans">` +
		`<rect width="100%" height="100%" fill="${T('surface')}"/>` +
		`<rect y="${CARD.height - 12}" width="100%" height="12" fill="${T('accent')}"/>` + inner + '</svg>';
}

/** The card as a PNG response. */
export function cardPng(/** @type {ReturnType<typeof cardData>} */ d) {
	const png = new Resvg(cardSvg(d), {
		fitTo: { mode: 'width', value: CARD.width },
		font: { fontFiles: loadFonts(), loadSystemFonts: false, defaultFontFamily: 'DM Sans' }
	}).render().asPng();
	return new Response(new Uint8Array(png), { headers: { 'content-type': 'image/png' } });
}

/**
 * The GET handler for the og.png endpoint next to a page.
 * @param {string} pageRoute the page's route id
 */
export const ogGet = (pageRoute) =>
	(/** @type {{params: Record<string, string | undefined>}} */ { params }) =>
		cardPng(cardData(pageRoute, params.slug));
