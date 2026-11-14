// Social preview metadata (titles, descriptions) and the 1200×630 PNG cards
// that og:image points to. Each page's card is prerendered by an og.png
// endpoint next to it; the page's meta and its card come from the same
// cardData(), so the description and the image always agree, and the image
// URL carries a hash of that data so social platforms refetch it when the
// numbers change.
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inflateSync } from 'node:zlib';
import { render } from 'svelte/server';
import { Resvg } from '@resvg/resvg-js';
import Parliament from '#lib/components/Parliament.svelte';
import { DEFAULT_BASE, baseOf } from '#lib/bases.js';
import { HOUSE_ORDER } from '#lib/parties.js';
import { votes, points, candidateName } from '#lib/format.js';
import { national, electorates } from '#lib/server/data.js';
import appCss from '../../app.css?raw';

export const SITE_NAME = '2026 special votes projection';
/** Where the site is served; og:url and og:image must be absolute. */
export const SITE_ORIGIN = 'https://czlee.nz';
export const CARD = { width: 1200, height: 630 };

const R = '/[[base=base]]';
const NUMBERS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
const listing = (/** @type {string[]} */ xs) =>
	xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`;
const minus = (/** @type {number} */ n) => (n > 0 ? `+${n}` : `−${-n}`);

/** Party short names, for a base year's national.json. */
const partyNames = (/** @type {any} */ n) =>
	Object.fromEntries([...n.parties, ...(n.base_parties ?? [])].map((/** @type {any} */ p) => [p.id, p.short]));

/** Everything the home card (and the home-ish pages' descriptions) shows. */
function homeData(/** @type {string} */ base) {
	const n = national(base);
	const names = partyNames(n);
	const ids = n.parties.map((/** @type {any} */ p) => p.id).filter((/** @type {string} */ id) =>
		n.seats.prelim[id]?.total || n.seats.projected[id]?.total);
	const changes = ids
		.map((/** @type {string} */ id) => ({ id, name: names[id], change: n.seats.projected[id].total - n.seats.prelim[id].total }))
		.filter((/** @type {any} */ c) => c.change)
		.sort((/** @type {any} */ a, /** @type {any} */ b) => b.change - a.change);
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'independent');
	const flips = electorates(base).filter((e) => e.flips).map((e) => {
		const rows = Object.fromEntries(e.candidate.rows.map((/** @type {any} */ r) => [r.key, r]));
		return { name: e.name, from: party(rows[e.prelim_winner].party), to: party(rows[e.winner].party) };
	});
	const seats = (/** @type {'prelim' | 'projected'} */ v) => Object.fromEntries(ids.map((/** @type {string} */ id) =>
		[id, { total: n.seats[v][id].total, electorate: n.seats[v][id].electorate }]));
	return {
		kind: 'home', base, hasElectorates: n.has_electorates, changes, flips, house: n.house,
		names: Object.fromEntries(ids.map((/** @type {string} */ id) => [id, names[id]])),
		seats: seats('projected'), compare: seats('prelim'), electorateCount: electorates(base).length
	};
}

/** "Green +1, Opportunity +1; Labour −1, NZ First −1." plus flips and House size. */
function homeSummary(/** @type {ReturnType<typeof homeData>} */ d) {
	const gains = d.changes.filter((c) => c.change > 0), losses = d.changes.filter((c) => c.change < 0);
	const fmt = (/** @type {any[]} */ cs) => cs.map((c) => `${c.name} ${minus(c.change)}`).join(', ');
	const parts = [];
	parts.push(d.changes.length ? `${[fmt(gains), fmt(losses)].filter(Boolean).join('; ')}.` : 'no seat changes.');
	if (d.flips.length === 1) parts.push(`${d.flips[0].name} flips from ${d.flips[0].from} to ${d.flips[0].to}.`);
	else if (d.flips.length) parts.push(`${cap(NUMBERS[d.flips.length] ?? String(d.flips.length))} electorates flip: ${listing(d.flips.map((f) => f.name))}.`);
	if (d.house.prelim !== d.house.projected) parts.push(`The House goes from ${d.house.prelim} to ${d.house.projected} seats.`);
	return parts.join(' ');
}
const cap = (/** @type {string} */ s) => s[0].toUpperCase() + s.slice(1);

/**
 * Everything an electorate card (and its page description) shows.
 * @returns {any} (omitted electorates have only a leader)
 */
function electorateData(/** @type {string} */ base, /** @type {string} */ slug) {
	const e = electorates(base).find((x) => x.slug === slug);
	if (!e) return null;
	const names = partyNames(national(base));
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'Independent');
	const common = { kind: 'electorate', base, name: e.name, roll: e.roll };
	if (e.omitted) {
		const label = e.winner_label.replace(/ \(.*\)$/, '');
		return { ...common, omitted: true, leader: { name: candidateName(label), party: party(e.winner_party), id: e.winner_party } };
	}
	const rows = Object.fromEntries(e.candidate.rows.map((/** @type {any} */ r) => [r.key, r]));
	const who = (/** @type {string} */ key) => {
		const r = rows[key];
		return { name: r.candidate ? candidateName(r.candidate) : r.label, party: party(r.party), id: r.party };
	};
	return {
		...common, omitted: false, flips: e.flips,
		prelim: { leader: who(e.prelim_winner), second: who(e.prelim_second), margin: e.prelim_margin, pct: e.prelim_margin_pct },
		projected: { leader: who(e.winner), second: who(e.second), margin: e.margin, pct: e.margin_pct }
	};
}

function electorateSummary(/** @type {NonNullable<ReturnType<typeof electorateData>>} */ d) {
	if (d.omitted) {
		return `Not projected: there was no ${d.base} electorate vote to project from. Held at the preliminary leader, ${d.leader.name} (${d.leader.party}).`;
	}
	const { prelim: a, projected: b } = /** @type {any} */ (d);
	const lead = `${b.leader.name} leads ${b.second.name} by ${votes(b.margin)} votes (${points(b.pct)})`;
	if (d.flips) {
		return `Projected to flip from ${a.leader.party} to ${b.leader.party}: ${lead}, after ${a.leader.name} led by ${votes(a.margin)} in the preliminary count.`;
	}
	const dir = Math.round(b.margin) > a.margin ? 'up from' : Math.round(b.margin) < a.margin ? 'down from' : 'the same as';
	return `Projected hold for ${b.leader.party}: ${lead}, ${dir} ${votes(a.margin)} in the preliminary count.`;
}

/**
 * The card for a route: the home card for every page but an electorate's.
 * @param {string | null} routeId @param {string} base @param {string | undefined} slug
 */
export function cardData(routeId, base, slug) {
	return (routeId === `${R}/electorate/[slug]` && slug && electorateData(base, slug)) || homeData(base);
}

/**
 * Title, description and image version for a page.
 * @param {string | null} routeId @param {string} base @param {string | undefined} slug
 */
export function pageMeta(routeId, base, slug) {
	const from = base === DEFAULT_BASE ? '' : ` from ${base}`;
	const using = `using ${base}’s special votes`;
	const data = cardData(routeId, base, slug);
	const version = createHash('sha1').update(JSON.stringify(data)).digest('hex').slice(0, 10);
	/** @type {{title: string, description: string}} */
	let m;
	if (data.kind === 'electorate') {
		const d = /** @type {NonNullable<ReturnType<typeof electorateData>>} */ (data);
		m = { title: `${d.name} · ${SITE_NAME}${from}`, description: electorateSummary(d) };
	} else {
		const d = /** @type {ReturnType<typeof homeData>} */ (data);
		if (routeId === `${R}/party-vote`) {
			m = {
				title: `Party vote projection · 2026 special votes${from}`,
				description: `How the 2026 preliminary party vote changes once ${base}’s special votes are applied, step by step, through to seats: ${homeSummary({ ...d, flips: [] })}`
			};
		} else if (routeId === `${R}/electorates`) {
			const f = d.flips;
			m = {
				title: `Electorates · 2026 special votes${from}`,
				description: `Projected final electorate results for all ${d.electorateCount} electorates, ${using}. ${
					f.length ? `${cap(NUMBERS[f.length] ?? String(f.length))} ${f.length === 1 ? 'flips' : 'flip'}: ${listing(f.map((x) => x.name))}.` : 'None flip.'}`
			};
		} else {
			m = {
				title: `${SITE_NAME}${from}`,
				description: `Projected final result from the preliminary count, ${using}: ${homeSummary(d)}`
			};
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
	// Builds run from site/, where node_modules is.
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

/** Shrinks a font size so roughly `chars` characters fit in `width` (DM Sans averages ~0.55em, less for lower case). */
const fit = (/** @type {string} */ s, /** @type {number} */ size, /** @type {number} */ width, em = 0.55) =>
	Math.min(size, Math.floor(width / (em * s.length)));
/** "leads by 140 (0.34 pp)", for an electorate card panel. */
const margin = (/** @type {string} */ verb, /** @type {any} */ r) => `${verb} by ${votes(r.margin)} (${points(r.pct)})`;

/** The site's horseshoe chart, as a standalone SVG fragment with literal colours. */
function horseshoe(/** @type {ReturnType<typeof homeData>} */ d) {
	const house = d.house.projected;
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
const footer = (/** @type {string} */ base) =>
	text(72, 572, 'czlee.nz/elections/2026-projection', { size: 24, weight: 600, fill: T('text-2') }) +
	text(1128, 572, `Using ${base}’s special votes · not an official result`, { size: 22, fill: T('text-3'), anchor: 'end' });

function homeSvg(/** @type {ReturnType<typeof homeData>} */ d) {
	const out = [kicker('New Zealand general election')];
	out.push(text(72, 168, '2026 special votes', { size: 66, weight: 700 }));
	out.push(text(72, 240, 'projection', { size: 66, weight: 700 }));
	let y = 318;
	// Up to four rows fit at full size; more get squeezed.
	const changes = d.changes.slice(0, 6);
	const [step, size] = changes.length > 4 ? [32, 26] : [50, 36];
	if (!changes.length) out.push(text(72, y, 'No seat changes', { size: 36, weight: 600 }));
	changes.forEach((c, i) => {
		const cy = y + i * step;
		out.push(`<circle cx="86" cy="${cy - size / 3}" r="${size / 3}" fill="${partyColour(c.id)}"/>`);
		out.push(text(112, cy, c.name, { size, weight: 600 }));
		out.push(text(400, cy, minus(c.change), { size, weight: 700, anchor: 'end' }));
	});
	y += (Math.max(1, changes.length) - 1) * step;
	// DM Sans has no → glyph, so these are in words.
	const notes = [];
	if (d.flips.length === 1) notes.push(`${d.flips[0].name} flips to ${d.flips[0].to}`);
	else if (d.flips.length) notes.push(`${d.flips.length} electorates flip`);
	if (d.house.prelim !== d.house.projected) notes.push(`${d.house.projected}-seat House`);
	if (!d.hasElectorates) notes.push('Party vote only');
	if (notes.length) out.push(text(72, y + 54, notes.join(' · '), { size: 28, fill: T('text-2') }));
	// The chart, on the right, as tall as the space allows.
	out.push(`<svg class="hs" x="660" y="56" width="480" height="440">${horseshoe(d)}</svg>`);
	out.push(text(900, 530, 'Projected seats · ringed: gained with specials', { size: 20, fill: T('text-3'), anchor: 'middle' }));
	out.push(footer(d.base));
	return out.join('');
}

function electorateSvg(/** @type {NonNullable<ReturnType<typeof electorateData>>} */ d) {
	const out = [kicker(`${SITE_NAME} · ${d.roll === 'maori' ? 'Māori' : 'general'} electorate`)];
	out.push(text(72, 180, d.name, { size: fit(d.name, 80, 1056), weight: 700 }));
	if (d.omitted) {
		out.push(text(72, 270, 'Not projected', { size: 40, weight: 600 }));
		out.push(text(72, 322, `No ${d.base} electorate vote to project from (by-election).`, { size: 30, fill: T('text-2') }));
		out.push(text(72, 372, `Held at the preliminary leader, ${d.leader.name} (${d.leader.party}).`, { size: 30, fill: T('text-2') }));
	} else {
		const { prelim: a, projected: b } = /** @type {any} */ (d);
		const badge = d.flips ? `Projected to flip from ${a.leader.party} to ${b.leader.party}` : `Projected ${b.leader.party} hold`;
		const bw = Math.round(badge.length * 0.5 * 28) + 48;
		out.push(`<rect x="72" y="214" width="${bw}" height="50" rx="25" fill="${d.flips ? partyColour(b.leader.id) : T('surface-2')}"/>`);
		out.push(text(96, 248, badge, { size: 28, weight: 600, fill: d.flips ? '#ffffff' : T('text') }));
		const panel = (/** @type {number} */ x, /** @type {string} */ label, /** @type {any} */ r, strong = false) => [
			`<rect x="${x}" y="300" width="500" height="210" rx="14" fill="${strong ? '#ffffff' : T('surface-2')}" stroke="${T('border')}"/>`,
			`<rect x="${x}" y="300" width="10" height="210" rx="5" fill="${partyColour(r.leader.id)}"/>`,
			text(x + 36, 348, label.toUpperCase(), { size: 20, weight: 600, fill: T('text-3'), spacing: 1.5 }),
			text(x + 36, 400, r.leader.name, { size: fit(r.leader.name, 40, 440), weight: 700 }),
			text(x + 36, 442, r.leader.party, { size: 28, weight: 600, fill: partyColour(r.leader.id) === T('party-other') ? T('text-2') : partyColour(r.leader.id) }),
			text(x + 36, 486, margin(strong ? 'projected to win' : 'leads', r), { size: fit(margin(strong ? 'projected to win' : 'leads', r), 28, 440, 0.46), fill: T('text-2') })
		].join('');
		out.push(panel(72, 'Preliminary count', a));
		out.push(`<path d="M586 405h22m-9-10l10 10-10 10" fill="none" stroke="${T('text-3')}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`);
		out.push(panel(628, 'Projected final', b, true));
	}
	out.push(footer(d.base));
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
		cardPng(cardData(pageRoute, baseOf(params.base), params.slug));
