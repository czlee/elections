<script>
	import { colour } from '#lib/parties.js';

	/**
	 * Horseshoe chamber chart: two straight legs of benches joined by an arch,
	 * seats running continuously up the left leg, round the arch and down the
	 * right leg. Filled dots are electorate seats, rings are list seats.
	 *
	 * @type {{
	 *   seats: Record<string, {total: number, electorate: number}>,
	 *   names: Record<string, string>,
	 *   compare?: Record<string, {total: number, electorate: number}>,
	 *   highlightLabel?: string,
	 *   majority: number,
	 *   overhang?: number
	 * }}
	 * compare: the other view's seats. Positions held by a different party
	 * there are marked (the seats that change hands between views). Only used
	 * when both views have the same number of seats, so positions line up.
	 */
	let { seats, names, compare = {}, highlightLabel = '', majority, overhang = 0 } = $props();

	// Left to right round the horseshoe. Sides are blocs, not a claim about who
	// governs; Opportunity has no declared side, so it sits at the top.
	const LEFT = ['labour', 'green', 'te-pati-maori'];
	const MIDDLE = ['top'];
	const RIGHT = ['nz-first', 'act', 'national'];
	const LANES = 4;
	const P = 17; // seat pitch
	const R = 6.6; // seat radius
	const R0 = 2.6 * P; // inner arch radius

	const fullOrder = (/** @type {string} */ p) => {
		const known = [...LEFT, ...MIDDLE, ...RIGHT];
		const i = known.indexOf(p);
		return i < 0 ? LEFT.length + MIDDLE.length - 0.5 : i; // others sit between the middle and the right
	};
	const order = $derived([
		...LEFT, ...MIDDLE,
		...Object.keys(seats).filter((p) => ![...LEFT, ...MIDDLE, ...RIGHT].includes(p)),
		...RIGHT
	].filter((p) => seats[p]?.total));
	const total = $derived(order.reduce((a, p) => a + seats[p].total, 0));
	/** Party at each position round the horseshoe, for a seats map (same party order). */
	const owners = (/** @type {Record<string, {total: number}>} */ m) =>
		order.concat(Object.keys(m).filter((p) => !order.includes(p) && m[p]?.total))
			.sort((a, b) => fullOrder(a) - fullOrder(b))
			.flatMap((p) => Array(m[p]?.total ?? 0).fill(p));
	const otherOwners = $derived.by(() => {
		const o = owners(compare);
		return o.length === total ? o : null;
	});

	/** Seat positions in order round the horseshoe, for n seats. */
	function layout(n) {
		const radii = Array.from({ length: LANES }, (_, i) => R0 + i * P);
		const arch = radii.map((r) => Math.round((Math.PI * r) / P));
		let archTotal = arch.reduce((a, b) => a + b, 0);
		const legRows = Math.max(0, Math.floor((n - archTotal) / (2 * LANES)));
		// Absorb any remainder into the arch, outer lanes first.
		for (let extra = n - archTotal - 2 * LANES * legRows, i = LANES - 1; extra > 0; extra--, i = (i - 1 + LANES) % LANES) {
			arch[i]++;
			archTotal++;
		}
		const outer = radii[LANES - 1];
		const cx = outer + P, cy = outer + P; // arch centre; legs hang below it
		const left = [], right = [], top = [];
		for (let row = 0; row < legRows; row++) {
			const y = cy + (legRows - row) * P; // row 0 is the bottom
			for (let lane = 0; lane < LANES; lane++) {
				left.push({ x: cx - radii[lane], y, key: row * LANES + (LANES - 1 - lane) });
				right.push({ x: cx + radii[lane], y, key: row * LANES + (LANES - 1 - lane) });
			}
		}
		radii.forEach((r, lane) => {
			const k = arch[lane];
			for (let j = 0; j < k; j++) {
				const a = Math.PI - ((j + 0.5) * Math.PI) / k;
				top.push({ x: cx + r * Math.cos(a), y: cy - r * Math.sin(a), a });
			}
		});
		left.sort((p, q) => p.key - q.key);
		right.sort((p, q) => q.key - p.key);
		top.sort((p, q) => q.a - p.a);
		return {
			pts: [...left, ...top, ...right],
			width: 2 * cx, height: cy + legRows * P + P, cx, cy, leg: legRows * LANES
		};
	}

	const geometry = $derived(layout(total));
	const dots = $derived.by(() => {
		const out = [];
		let i = 0;
		for (const p of order) {
			const { total: n, electorate } = seats[p];
			const start = i;
			// Electorate seats at the end of the block that's further from the top centre.
			const leftHalf = start + n / 2 < total / 2;
			// If the block shares a leg row with its neighbour (left leg: at its start;
			// right leg: at its end), make those shared seats list seats and start the
			// electorate seats at the next full row, as long as they stay in the leg.
			const leg = geometry.leg;
			let shift = 0;
			if (leftHalf && start < leg) {
				const k = (LANES - (start % LANES)) % LANES;
				if (k && n - electorate >= k && start + k + electorate <= leg) shift = k;
			} else if (!leftHalf && start + n > total - leg) {
				const k = (total - (start + n)) % LANES ? LANES - ((total - (start + n)) % LANES) : 0;
				if (k && n - electorate >= k && start + n - k - electorate >= total - leg) shift = k;
			}
			for (let j = 0; j < n; j++) {
				const isElectorate = leftHalf
					? j >= shift && j < shift + electorate
					: j >= n - shift - electorate && j < n - shift;
				const marked = otherOwners !== null && otherOwners[i] !== p;
				out.push({ ...geometry.pts[i++], party: p, electorate: isElectorate, marked });
			}
		}
		return out;
	});
	const blocTotal = (/** @type {string[]} */ ps) => ps.reduce((a, p) => a + (seats[p]?.total ?? 0), 0);
	// Legend lines: left bloc, the middle, right bloc (largest party first).
	const others = $derived(Object.keys(seats).filter((p) => seats[p]?.total && ![...LEFT, ...MIDDLE, ...RIGHT].includes(p)));
	const blocs = $derived([
		{ key: 'left', parties: LEFT.filter((p) => seats[p]?.total), label: 'left bloc' },
		{ key: 'middle', parties: [...MIDDLE, ...others].filter((p) => seats[p]?.total), label: '' },
		{ key: 'right', parties: [...RIGHT].reverse().filter((p) => seats[p]?.total), label: 'right bloc' }
	]);
</script>

<figure>
	<svg viewBox="0 0 {geometry.width} {geometry.height}" role="img"
		aria-label="{total} seats: {order.map((p) => `${names[p]} ${seats[p].total}`).join(', ')}">
		<line class="majority" x1={geometry.cx} x2={geometry.cx} y1={geometry.cy - R0 - P * (LANES - 0.4)} y2={geometry.cy - R0 + P * 1.6} />
		<text class="maj" x={geometry.cx} y={geometry.cy - R0 + P * 2.6} text-anchor="middle">{total} seats</text>
		{#if overhang}
			<text x={geometry.cx} y={geometry.cy - R0 + P * 3.6} text-anchor="middle">({overhang} overhang)</text>
		{/if}
		<text x={geometry.cx} y={geometry.cy - R0 + P * 5.2} text-anchor="middle">{majority} for majority</text>
		{#each dots as d, i (i)}
			{#if d.marked}
				<circle class="halo" cx={d.x} cy={d.y} r={R + 2.2} />
			{/if}
			{#if d.electorate}
				<circle cx={d.x} cy={d.y} r={R} fill={colour(d.party)}>
					<title>{names[d.party]}: electorate seat</title>
				</circle>
			{:else}
				<circle cx={d.x} cy={d.y} r={R - 1.6} fill="var(--surface)" stroke={colour(d.party)} stroke-width="3.2">
					<title>{names[d.party]}: list seat</title>
				</circle>
			{/if}
		{/each}
	</svg>
	<div class="blocs">
		{#each blocs as b (b.key)}
			{#if b.parties.length}
				<p>
					{#each b.parties as p (p)}
						<span class="party"><span class="swatch" style:background={colour(p)}></span>{names[p]} <strong>{seats[p].total}</strong></span>
					{/each}
					{#if b.label}<span class="muted">({b.label}: {blocTotal(b.parties)})</span>{/if}
				</p>
			{/if}
		{/each}
	</div>
	<ul class="legend small muted">
		<li><span class="key filled"></span>electorate</li>
		<li><span class="key ring"></span>list</li>
		{#if highlightLabel && dots.some((d) => d.marked)}
			<li><span class="key halo-key"></span>{highlightLabel}</li>
		{/if}
	</ul>
</figure>

<style>
	figure { margin: 0; }
	svg { width: 100%; max-width: 304px; display: block; margin: 0 auto; }
	.halo { fill: none; stroke: var(--text); stroke-width: 1.3; }
	.majority { stroke: var(--text-3); stroke-dasharray: 3 3; }
	svg text { font-size: 10px; }
	.maj { font-size: 11px; }
	.maj { fill: var(--text); font-weight: 600; }
	.blocs { margin-top: 0.5em; font-size: 0.9rem; }
	.blocs p { margin: 0.15em 0; display: flex; flex-wrap: wrap; gap: 0.1em 1em; }
	.blocs strong { font-variant-numeric: tabular-nums; }
	.legend {
		list-style: none; padding: 0; margin: 0.3em 0 0; display: flex; flex-wrap: wrap;
		gap: 0.2em 1em; font-size: 0.9rem;
	}
	.legend.small { font-size: 0.8rem; }
	.key { display: inline-block; width: 0.8em; height: 0.8em; border-radius: 50%; margin-right: 0.35em; vertical-align: -0.05em; }
	.key.filled { background: var(--text-2); }
	.key.ring { border: 2.5px solid var(--text-2); }
	.key.halo-key { width: 1em; height: 1em; border: 1.25px solid var(--text); vertical-align: -0.15em; }
</style>
