<script>
	// Diverging bars of each party's change in share (percentage points), from 0.
	import { scaleLinear } from 'd3-scale';
	import { colour } from '#lib/parties.js';
	import { pp, pct } from '#lib/format.js';

	/** @type {{rows: {id: string, label: string, from: number, to: number}[]}} */
	let { rows } = $props();

	const ROW = 24, RIGHT = 74, TOP = 22;
	let width = $state(640);
	const W = $derived(Math.max(300, width));
	const LABEL = $derived(Math.min(120, Math.round(W * 0.3)));
	const ext = $derived(Math.max(...rows.map((r) => Math.abs(r.to - r.from))) * 1.1);
	const x = $derived(scaleLinear().domain([-ext, ext]).range([LABEL, W - RIGHT]).nice());
	const ticks = $derived(x.ticks(6));
</script>

<div class="chart" bind:clientWidth={width}>
<svg width={W} viewBox="0 0 {W} {TOP + rows.length * ROW + 6}" role="img" aria-label="Change in party vote share">
	{#each ticks as t (t)}
		<line class="grid" class:zero={t === 0} x1={x(t)} x2={x(t)} y1={TOP - 6} y2={TOP + rows.length * ROW} />
		<text x={x(t)} y={TOP - 10} text-anchor="middle" class="tick">{t > 0 ? '+' : ''}{(100 * t).toFixed(1)}</text>
	{/each}
	{#each rows as r, i (r.id)}
		{@const y = TOP + i * ROW}
		{@const d = r.to - r.from}
		<g>
			<title>{r.label}: {pct(r.from)} → {pct(r.to)} ({pp(d)})</title>
			<rect x="0" y={y} width={W} height={ROW} fill="transparent" />
			<text x={LABEL - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label">{r.label}</text>
			<rect x={Math.min(x(0), x(d))} y={y + 5} width={Math.max(1, Math.abs(x(d) - x(0)))} height={ROW - 10} rx="2"
				fill={colour(r.id)} />
			<text x={W - RIGHT + 6} y={y + ROW / 2 + 4} class="value">{pp(d)}</text>
		</g>
	{/each}
</svg>
</div>
<p class="small muted">Change from preliminary share to projected final share, percentage points.</p>

<style>
	.chart { width: 100%; max-width: 720px; }
	svg { display: block; max-width: 100%; height: auto; }
	.grid { stroke: var(--grid); }
	.grid.zero { stroke: var(--text-3); }
	.tick { font-size: 11px; }
	.label { font-size: 13px; fill: var(--text); }
	.value { font-size: 12px; font-variant-numeric: tabular-nums; }
</style>
