<script>
	import { colour } from '#lib/parties.js';

	/**
	 * A Westminster-style chamber, as in the NZ debating chamber: two sets of
	 * benches facing each other across the aisle, the Speaker's chair at the
	 * left, and cross-benches at the far (right) end.
	 *
	 * @type {{
	 *   seats: Record<string, number>,
	 *   names: Record<string, string>,
	 *   highlight?: Record<string, number>,
	 *   highlightLabel?: string,
	 *   majority: number
	 * }}
	 * seats: party_id → seats. highlight: party_id → how many of that party's
	 * seats to ring (the seats that change between views).
	 */
	let { seats, names, highlight = {}, highlightLabel = '', majority } = $props();

	// Sides by party, nearest the Speaker first. Sides are blocs, not a claim
	// about who governs; Opportunity has no declared side.
	const TOP_SIDE = ['labour', 'green', 'te-pati-maori'];
	const BOTTOM_SIDE = ['national', 'act', 'nz-first'];
	const CROSS = ['top'];
	const ROWS = 4; // benches per side
	const CROSS_ROWS = 4;
	const S = 16; // seat pitch
	const R = 6.2; // seat radius
	const AISLE = 30;
	const LEFT = 44; // room for the Speaker's chair

	const known = [...TOP_SIDE, ...BOTTOM_SIDE, ...CROSS];
	const others = $derived(Object.keys(seats).filter((p) => !known.includes(p) && seats[p]));

	/**
	 * Fills a block of `rows` rows column by column, so each party takes
	 * whole columns as far as possible. `dir` is +1 (rows go down from y0) or
	 * −1 (rows go up from y0).
	 */
	function bench(parties, rows, x0, y0, dir) {
		const out = [];
		let i = 0;
		for (const p of parties) {
			const n = seats[p] ?? 0;
			const ringed = highlight[p] ?? 0;
			for (let j = 0; j < n; j++, i++) {
				const col = Math.floor(i / rows), row = i % rows;
				out.push({ x: x0 + col * S, y: y0 + dir * row * S, party: p, ring: j >= n - ringed });
			}
		}
		return { dots: out, cols: Math.ceil(i / rows), n: i };
	}

	const layout = $derived.by(() => {
		const top = bench(TOP_SIDE, ROWS, LEFT, 0, -1);
		const bottom = bench(BOTTOM_SIDE, ROWS, LEFT, 0, 1);
		const cols = Math.max(top.cols, bottom.cols);
		const crossX = LEFT + cols * S + 22;
		const cross = bench([...CROSS, ...others], CROSS_ROWS, crossX, 0, 1);
		const yTop = (ROWS - 1) * S + 14; // offset so the top block's back row is at y = 14
		const shift = (/** @type {any[]} */ ds, dy) => ds.map((d) => ({ ...d, y: d.y + dy }));
		const yBottom = yTop + AISLE;
		const crossTop = yTop + AISLE / 2 - ((CROSS_ROWS - 1) * S) / 2;
		const dots = [
			...shift(top.dots, yTop),
			...shift(bottom.dots, yBottom),
			...shift(cross.dots, crossTop)
		];
		const width = crossX + Math.max(1, cross.cols) * S + 8;
		const height = yBottom + (ROWS - 1) * S + 14;
		return {
			dots, width, height, aisleY: yTop + AISLE / 2, top: top.n, bottom: bottom.n, cross: cross.n,
			crossX, benchEnd: LEFT + cols * S
		};
	});
	const total = $derived(layout.top + layout.bottom + layout.cross);
	const sideLabel = (/** @type {string[]} */ ps) =>
		ps.filter((p) => seats[p]).map((p) => names[p]).join(' + ');
</script>

<figure>
	<svg viewBox="0 0 {layout.width} {layout.height}" role="img"
		aria-label="{total} seats: {Object.keys(seats).filter((p) => seats[p]).map((p) => `${names[p]} ${seats[p]}`).join(', ')}">
		<rect class="speaker" x="6" y={layout.aisleY - 9} width="22" height="18" rx="3">
			<title>Speaker's chair</title>
		</rect>
		<line class="aisle" x1={LEFT - 8} x2={layout.benchEnd} y1={layout.aisleY} y2={layout.aisleY} />
		{#each layout.dots as d, i (i)}
			<circle cx={d.x} cy={d.y} r={R} fill={colour(d.party)}>
				<title>{names[d.party]}: {seats[d.party]} seats</title>
			</circle>
			{#if d.ring}
				<circle class="ring" cx={d.x} cy={d.y} r={R + 2.5} />
			{/if}
		{/each}
	</svg>
	<div class="sides small">
		<span><strong>{layout.top}</strong> {sideLabel(TOP_SIDE)}</span>
		<span><strong>{layout.bottom}</strong> {sideLabel(BOTTOM_SIDE)}</span>
		{#if layout.cross}<span><strong>{layout.cross}</strong> cross-benches</span>{/if}
		<span class="muted">{total} seats, {majority} for a majority</span>
	</div>
	<ul class="legend">
		{#each [...TOP_SIDE, ...BOTTOM_SIDE, ...CROSS, ...others].filter((p) => seats[p]) as p (p)}
			<li><span class="swatch" style:background={colour(p)}></span>{names[p]} <strong>{seats[p]}</strong></li>
		{/each}
		{#if highlightLabel && Object.values(highlight).some((v) => v)}
			<li class="muted"><span class="ring-key"></span>{highlightLabel}</li>
		{/if}
	</ul>
</figure>

<style>
	figure { margin: 0; }
	svg { width: 100%; max-width: 640px; display: block; }
	.speaker { fill: none; stroke: var(--text-3); stroke-width: 1.5; }
	.aisle { stroke: var(--grid); stroke-width: 1; stroke-dasharray: 3 3; }
	.ring { fill: none; stroke: var(--text); stroke-width: 2; }
	.sides { display: flex; flex-wrap: wrap; gap: 0.2em 1.2em; margin-top: 0.4em; }
	.legend {
		list-style: none; padding: 0; margin: 0.3em 0 0; display: flex; flex-wrap: wrap;
		gap: 0.2em 1em; font-size: 0.9rem;
	}
	.legend strong, .sides strong { font-variant-numeric: tabular-nums; }
	.ring-key {
		display: inline-block; width: 0.8em; height: 0.8em; border-radius: 50%;
		border: 2px solid var(--text); margin-right: 0.35em; vertical-align: -0.05em;
	}
</style>
