// Social preview metadata (titles, descriptions) and the 1200×630 PNG cards
// that og:image points to. Each page's card is prerendered by an og.png
// endpoint next to it; the page's meta and its card come from the same
// cardData(), so the description and the image always agree, and the image
// URL carries a hash of that data and of the code that draws the card, so
// social platforms refetch it when the numbers or the design change.
// Adapted from the maori-to-general site's og.js.
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { inflateSync } from 'node:zlib';
import { error } from '@sveltejs/kit';
import { render } from 'svelte/server';
import { Resvg } from '@resvg/resvg-js';
import Parliament from '#lib/components/Parliament.svelte';
import { HOUSE_ORDER } from '#lib/parties.js';
import { votes, candidateName } from '#lib/format.js';
import { DATA, ELECTIONS, partyKey, seatsOf } from '#lib/elections.js';
import appCss from '../../app.css?raw';
import ogSource from './og.js?raw';
import parliamentSource from '#lib/components/Parliament.svelte?raw';

export const SITE_NAME = 'New Zealand election margins';
/** Where the site is served; og:url and og:image must be absolute. */
export const SITE_ORIGIN = 'https://czlee.nz';
export const CARD = { width: 1200, height: 630 };

const SITE_DESCRIPTION =
	'How many party votes it would take for a party to gain or lose a seat, and the closest electorates, for New Zealand general elections.';

/** Seats by party key, with each party's change from `base` (the actual House) to `house`. */
const changedParties = (/** @type {any} */ base, /** @type {any} */ house) => {
	const was = seatsOf(base), now = seatsOf(house);
	return Object.keys(now).filter((id) => now[id].total !== (was[id]?.total ?? 0))
		.map((id) => ({ id, change: now[id].total - (was[id]?.total ?? 0) }));
};

/**
 * The party closest to gaining (`dir` 'gain') or losing ('lose') a seat: the
 * smallest number of party votes, more or fewer, that would do it.
 */
function closestParty(/** @type {any} */ d, /** @type {'gain' | 'lose'} */ dir) {
	/** @type {any} */
	let best = null;
	for (const p of d.parties) {
		const s = p[dir];
		if (s && (!best || s.votes < best.votes)) best = { p, dir, votes: s.votes, house: s.house };
	}
	if (!best) return null;
	// Who gets the seat a party loses, or loses the seat a party gains (the other side of the same swap).
	const other = changedParties(d.house, best.house).filter((c) => c.id !== partyKey(best.p) && c.change * (best.dir === 'gain' ? -1 : 1) > 0);
	const names = Object.fromEntries([...d.parties, ...d.house.parties].map((/** @type {any} */ p) => [partyKey(p), p.name]));
	return { id: partyKey(best.p), name: best.p.name, dir: /** @type {'gain' | 'lose'} */ (best.dir), votes: best.votes,
		other: other.length === 1 ? names[other[0].id] ?? null : null };
}

/** The closest loss and the closest gain (either may be missing). */
const closestBoth = (/** @type {any} */ d) => ({ lose: closestParty(d, 'lose'), gain: closestParty(d, 'gain') });

/** The closest electorate, if the data has any. */
function closestElectorate(/** @type {any} */ d) {
	const e = d.electorates?.[0];
	if (!e) return null;
	return { name: e.electorate, margin: e.margin, winner: e.winner_party_name ?? 'Independent',
		runnerUp: e.runner_up_party_name ?? 'Independent', winnerName: candidateName(e.winner) };
}

/** Everything an election's card (and its page's description) shows. */
function electionData(/** @type {string} */ id) {
	const e = ELECTIONS.find((x) => x.id === id);
	const d = DATA[id];
	if (!e || !d) return null;
	const names = Object.fromEntries([...d.parties, ...d.house.parties].map((/** @type {any} */ p) => [partyKey(p), p.name]));
	return {
		kind: 'election', year: e.year, prelim: e.prelim,
		closest: closestBoth(d), electorate: closestElectorate(d),
		seats: seatsOf(d.house), names: { independent: 'Independent', ...names },
		houseSize: /** @type {number} */ (d.house.house), totalSeats: /** @type {number} */ (d.total_seats)
	};
}

/** The home card's data when there's no 2026 final result to feature: static, with no results on it. */
const homeData = () => ({ kind: /** @type {const} */ ('home') });

/**
 * The card for a page: an election's, or for the home page the 2026 final results' card (the
 * static home card if there's no 2026 final). Platforms cache a card by its page's URL, so
 * the home URL needs a rescrape (Facebook Sharing Debugger, LinkedIn Post Inspector) when this changes.
 */
export function cardData(/** @type {string | undefined} */ election) {
	return (election ? electionData(election) : electionData('2026')) || homeData();
}

const sentence = (/** @type {NonNullable<ReturnType<typeof closestParty>>} */ c) =>
	c.dir === 'gain'
		? `${votes(c.votes)} more party votes would give ${c.name} an extra seat${c.other ? `, taking one from ${c.other}` : ''}`
		: `${votes(c.votes)} fewer party votes would cost ${c.name} a seat${c.other ? `, which would go to ${c.other}` : ''}`;

/** Everything that draws a card, so a design change gives it a new URL too. */
const LAYOUT = ogSource + parliamentSource + appCss;

/** Title, description and image version for a page. */
export function pageMeta(/** @type {string | undefined} */ election) {
	const data = cardData(election);
	const version = createHash('sha1').update(JSON.stringify(data)).update(LAYOUT).digest('hex').slice(0, 10);
	// The home page shows the 2026 card but keeps the site's own title and description.
	if (election && data.kind === 'election') {
		const d = /** @type {NonNullable<ReturnType<typeof electionData>>} */ (data);
		const parts = [d.closest.lose && `${sentence(d.closest.lose)}.`, d.closest.gain && `${sentence(d.closest.gain)}.`,
			d.electorate && `Closest electorate: ${d.electorate.name}, by ${votes(d.electorate.margin)} ${d.electorate.margin === 1 ? 'vote' : 'votes'}.`,
			d.prelim ? 'Based on the preliminary count.' : ''].filter(Boolean);
		return {
			title: `${d.year} ${SITE_NAME}${d.prelim ? ' (preliminary)' : ''}`,
			description: parts.join(' ') ||
				`How many party votes it would take for each party to gain or lose a seat at the ${d.year} New Zealand general election, and the closest electorates.`,
			version
		};
	}
	return { title: SITE_NAME, description: SITE_DESCRIPTION, version };
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
 * Figtree as TTF files in a temporary directory. (resvg-js's Node build
 * ignores `fontBuffers`, and then loads the system fonts, so it gets paths.)
 */
function loadFonts() {
	if (fonts) return fonts;
	// Builds run from the site's directory, where node_modules is.
	const src = `${process.cwd()}/node_modules/@fontsource/figtree/files`;
	const dir = mkdtempSync(join(tmpdir(), 'og-fonts-'));
	return (fonts = ['latin', 'latin-ext'].flatMap((subset) => [400, 600, 700].map((w) => {
		const file = join(dir, `figtree-${subset}-${w}.ttf`);
		writeFileSync(file, woffToSfnt(readFileSync(`${src}/figtree-${subset}-${w}-normal.woff`)));
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
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="100" font-family="Figtree">` +
		text(0, 60, s, { size, weight }) + '</svg>';
	const box = new Resvg(svg, { font: { fontFiles: loadFonts(), loadSystemFonts: false, defaultFontFamily: 'Figtree' } }).getBBox();
	return box ? box.width : s.length * 0.55 * size;
}

/** The largest font size, up to `size`, at which `s` fits in `width`. */
const fitText = (/** @type {string} */ s, /** @type {number} */ size, /** @type {number} */ width, weight = 400) =>
	Math.min(size, Math.floor(size * width / textWidth(s, size, weight)));

/** Breaks `s` into lines no wider than `width` at `size`, at spaces. */
function wrap(/** @type {string} */ s, /** @type {number} */ size, /** @type {number} */ width, weight = 400) {
	/** @type {string[]} */
	const lines = [];
	let line = '';
	for (const word of s.split(' ')) {
		const next = line ? `${line} ${word}` : word;
		if (line && textWidth(next, size, weight) > width) { lines.push(line); line = word; } else line = next;
	}
	return line ? [...lines, line] : lines;
}

/** The site's horseshoe chart, as a standalone SVG fragment with literal colours. */
function horseshoe(/** @type {NonNullable<ReturnType<typeof electionData>>} */ d) {
	const { body } = render(Parliament, {
		props: { seats: d.seats, names: d.names, majority: Math.floor(d.houseSize / 2) + 1, overhang: Math.max(0, d.houseSize - d.totalSeats) }
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
const footer = (/** @type {string} */ note) =>
	text(72, 572, 'czlee.nz/elections/margins', { size: 24, weight: 600, fill: T('text-2') }) +
	text(1128, 572, note, { size: 22, fill: T('text-3'), anchor: 'end' });

/** A dot in a party's colour with its name, for a card row. */
const partyDot = (/** @type {string} */ id, /** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ r = 10) =>
	`<circle cx="${x}" cy="${y}" r="${r}" fill="${partyColour(id)}"/>`;

function electionSvg(/** @type {NonNullable<ReturnType<typeof electionData>>} */ d) {
	const out = [kicker(`New Zealand general election${d.prelim ? ' · preliminary count' : ''}`, 82)];
	out.push(text(72, 150, `${d.year} election margins`, { size: 56, weight: 700 }));
	let y = 206;
	for (const c of [d.closest.lose, d.closest.gain]) {
		if (!c) continue;
		out.push(text(72, y, (c.dir === 'gain' ? 'Closest to gaining a seat' : 'Closest to losing a seat').toUpperCase(),
			{ size: 20, weight: 600, fill: T('text-3'), spacing: 1.5 }));
		out.push(partyDot(c.id, 86, y + 38, 12));
		const head = `${c.name}: ${votes(c.votes)} votes`;
		out.push(text(110, y + 52, head, { size: fitText(head, 46, 480, 700), weight: 700, fill: T('text') }));
		const rest = c.dir === 'gain'
			? `more party votes would give ${c.name} an extra seat${c.other ? `, at ${c.other}’s expense` : ''}`
			: `fewer party votes would cost ${c.name} a seat${c.other ? `, which would go to ${c.other}` : ''}`;
		const lines = wrap(rest, 26, 560);
		lines.forEach((l, i) => out.push(text(72, y + 90 + i * 32, l, { size: 26, fill: T('text-2') })));
		y += 90 + lines.length * 32 + 36;
	}
	out.push(`<svg class="hs" x="660" y="56" width="480" height="440">${horseshoe(d)}</svg>`);
	out.push(text(900, 530, 'The House · filled: electorate, ring: list', { size: 20, fill: T('text-3'), anchor: 'middle' }));
	out.push(footer(d.prelim ? 'Preliminary count · not an official result' : 'Not an official result'));
	return out.join('');
}

function homeSvg() {
	const out = [kicker('New Zealand general elections', 82)];
	out.push(text(72, 160, 'Election margins', { size: 72, weight: 700 }));
	out.push(text(72, 226, 'How many party votes it takes to gain or lose a seat', { size: 32, fill: T('text-2') }));
	const rows = [
		['Closest to losing a seat', 'how many fewer party votes would cost a party a seat'],
		['Closest to gaining a seat', 'how many more party votes would win one'],
		['Closest electorates', 'the narrowest margins between the winner and runner-up']
	];
	rows.forEach(([head, rest], i) => {
		const y = 320 + i * 84;
		out.push(`<rect x="72" y="${y - 34}" width="8" height="64" rx="4" fill="${T('accent')}"/>`);
		out.push(text(100, y - 2, head, { size: 34, weight: 700 }));
		out.push(text(100, y + 28, rest, { size: 26, fill: T('text-2') }));
	});
	out.push(footer('Not an official result'));
	return out.join('');
}

/** The card as SVG markup. */
export function cardSvg(/** @type {ReturnType<typeof cardData>} */ d) {
	const inner = d.kind === 'election' ? electionSvg(/** @type {any} */ (d)) : homeSvg();
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD.width}" height="${CARD.height}" viewBox="0 0 ${CARD.width} ${CARD.height}" font-family="Figtree">` +
		`<rect width="100%" height="100%" fill="${T('surface')}"/>` +
		`<rect y="${CARD.height - 12}" width="100%" height="12" fill="${T('accent')}"/>` + inner + '</svg>';
}

/** The card as a PNG response. */
export function cardPng(/** @type {ReturnType<typeof cardData>} */ d) {
	const png = new Resvg(cardSvg(d), {
		fitTo: { mode: 'width', value: CARD.width },
		font: { fontFiles: loadFonts(), loadSystemFonts: false, defaultFontFamily: 'Figtree' }
	}).render().asPng();
	return new Response(new Uint8Array(png), { headers: { 'content-type': 'image/png' } });
}

/** The GET handler for the og.png endpoint next to a page. */
export const ogGet = () =>
	(/** @type {{params: Record<string, string | undefined>}} */ { params }) => {
		if (params.election && !electionData(params.election)) error(404, 'No such election');
		return cardPng(cardData(params.election));
	};
