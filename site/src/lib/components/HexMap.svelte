<script>
	// Equal-area hex map of the 71 electorates (layout from export_hexmap.py),
	// coloured by leading party. General electorates on the left; the seven
	// Māori electorates, which overlap them geographically, as a separate group.
	import hexmap from '#lib/data/hexmap.json';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { pct, candidateName } from '#lib/format.js';

	/** @type {{electorates: any[], names: Record<string, string>, view: 'prelim' | 'projected'}} */
	let { electorates, names, view } = $props();

	const SIZE = 13; // hex circumradius
	const SQRT3 = Math.sqrt(3);
	const GAP = 1.2; // surface gap between hexes
	const pos = (/** @type {number[]} */ [q, r]) => [SIZE * SQRT3 * (q + r / 2), SIZE * 1.5 * r];

	const byName = $derived(Object.fromEntries(electorates.map((e) => [e.name, e])));
	const geometry = $derived.by(() => {
		const general = Object.entries(hexmap.general).map(([name, qr]) => ({ name, xy: pos(qr) }));
		const maori = Object.entries(hexmap.maori).map(([name, qr]) => ({ name, xy: pos(qr) }));
		const gx = general.map((h) => h.xy[0]), gy = general.map((h) => h.xy[1]);
		const mx = maori.map((h) => h.xy[0]), my = maori.map((h) => h.xy[1]);
		const pad = SIZE + 4;
		const ox = -Math.min(...gx) + pad, oy = -Math.min(...gy) + pad + 16;
		// Māori group: to the right of the general map, a little below the top.
		const mox = Math.max(...gx) + ox + 3.2 * SIZE - Math.min(...mx);
		const moy = oy + 3 * SIZE - Math.min(...my);
		const hexes = [
			...general.map((h) => ({ ...h, x: h.xy[0] + ox, y: h.xy[1] + oy })),
			...maori.map((h) => ({ ...h, x: h.xy[0] + mox, y: h.xy[1] + moy }))
		];
		const width = Math.max(...hexes.map((h) => h.x)) + pad;
		const height = Math.max(...hexes.map((h) => h.y)) + pad;
		return {
			hexes, width, height,
			maoriLabel: { x: Math.min(...mx) + mox - SIZE, y: Math.min(...my) + moy - SIZE - 8 }
		};
	});

	const r = SIZE - GAP;
	const hexPath = Array.from({ length: 6 }, (_, i) => {
		const a = (Math.PI / 3) * i + Math.PI / 6;
		return `${(r * Math.cos(a)).toFixed(2)},${(r * Math.sin(a)).toFixed(2)}`;
	}).join(' ');

	/** Leader in the chosen count: {party, label, margin} */
	function leader(/** @type {any} */ e) {
		if (!e) return null;
		if (e.omitted) return { party: e.winner_party, who: e.winner_label, margin: null };
		return view === 'prelim'
			? { party: e.prelim_winner_party, who: e.prelim_winner, margin: e.prelim_margin_pct }
			: { party: e.winner_party, who: e.winner, margin: e.margin_pct };
	}

	let hovered = $state(/** @type {string | null} */ (null));
	const hoveredInfo = $derived.by(() => {
		const e = hovered ? byName[hovered] : null;
		const l = leader(e);
		if (!e || !l) return null;
		const party = l.party ? names[l.party] ?? l.party : 'independent';
		if (e.omitted) return `${e.name}: not projected (preliminary leader ${party})`;
		const who = candidateName(l.who);
		return `${e.name}: ${who} (${party}) leads by ${pct(l.margin)}${e.flips ? ' · flips with specials' : ''}`;
	});
	const parties = $derived(
		[...new Set(electorates.map((e) => leader(e)?.party))].map((p) => ({
			id: p, n: electorates.filter((e) => leader(e)?.party === p).length
		})).sort((a, b) => b.n - a.n)
	);
</script>

<figure>
	<svg viewBox="0 0 {geometry.width} {geometry.height}" role="img"
		aria-label="Hex map of electorates by {view === 'prelim' ? 'preliminary' : 'projected'} leader">
		<text x="4" y="12" class="group">General</text>
		<text x={geometry.maoriLabel.x} y={geometry.maoriLabel.y} class="group">Māori</text>
		{#each geometry.hexes as h (h.name)}
			{@const e = byName[h.name]}
			{@const l = leader(e)}
			<a href={link(`/electorate/${e?.slug}/`)} aria-label={h.name}
				onmouseenter={() => (hovered = h.name)} onmouseleave={() => (hovered = null)}
				onfocus={() => (hovered = h.name)} onblur={() => (hovered = null)}>
				<polygon points={hexPath} transform="translate({h.x},{h.y})" fill={colour(l?.party)}
					class:omitted={e?.omitted} class:hover={hovered === h.name}>
					<title>{h.name}</title>
				</polygon>
				{#if e?.flips}
					<polygon points={hexPath} transform="translate({h.x},{h.y}) scale(0.55)" class="flip" />
				{/if}
			</a>
		{/each}
	</svg>
	<p class="caption small" aria-live="polite">{hoveredInfo ?? 'Hover over or tap an electorate.'}</p>
	<ul class="legend small">
		{#each parties as p (p.id)}
			<li><span class="swatch" style:background={colour(p.id)}></span>{p.id ? names[p.id] ?? p.id : 'Other'} {p.n}</li>
		{/each}
		<li><span class="flip-key"></span>flips with specials</li>
		<li><span class="omit-key"></span>not projected</li>
	</ul>
</figure>

<style>
	figure { margin: 0; }
	svg { width: 100%; max-width: 420px; display: block; }
	polygon { stroke: var(--surface); stroke-width: 0; transition: opacity 0.1s; }
	polygon.hover { stroke: var(--text); stroke-width: 2; }
	polygon.omitted { opacity: 0.45; }
	polygon.flip { fill: none; stroke: var(--surface); stroke-width: 2.5; pointer-events: none; }
	.group { font-size: 11px; font-weight: 600; fill: var(--text-2); }
	.caption { min-height: 2.6em; margin: 0.3em 0; color: var(--text); }
	.legend { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.15em 0.9em; }
	.flip-key, .omit-key {
		display: inline-block; width: 0.8em; height: 0.8em; margin-right: 0.35em; vertical-align: -0.05em;
		background: var(--text-3); border-radius: 2px;
	}
	.flip-key { box-shadow: inset 0 0 0 2px var(--text-3), inset 0 0 0 3.5px var(--surface); }
	.omit-key { opacity: 0.45; }
</style>
