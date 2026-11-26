<script>
	// Horizontal bars from 1 (no change) to each multiplier: above 1 means the
	// party did better among special votes than in the preliminary count.
	import { scaleLinear } from 'd3-scale';
	import { colour } from '#lib/parties.js';
	import { mult } from '#lib/format.js';

	/** @type {{rows: {id: string, label: string, short?: string, value: number, party?: string | null, note?: string}[]}} */
	let { rows } = $props();

	const ROW = 24, RIGHT = 60, TOP = 22;
	let width = $state(640);
	const W = $derived(Math.max(300, width));
	const LABEL = $derived(Math.min(160, Math.round(W * 0.3)));
	const ext = $derived(Math.max(...rows.map((r) => Math.abs(Math.log(r.value)))));
	const lo = $derived(Math.min(0.5, Math.exp(-ext) * 0.95)), hi = $derived(Math.max(2, Math.exp(ext) * 1.05));
	// Log scale so 0.5 and 2 are the same distance from 1.
	const x = $derived(scaleLinear().domain([Math.log(lo), Math.log(hi)]).range([LABEL, W - RIGHT]));
	const ticks = $derived([0.5, 0.75, 1, 1.5, 2, 3].filter((t) => t >= lo && t <= hi));
</script>

<div class="chart" bind:clientWidth={width}>
<svg width={W} viewBox="0 0 {W} {TOP + rows.length * ROW + 6}" role="img" aria-label="Special-vote multiplier by party">
	{#each ticks as t (t)}
		<line class:one={t === 1} class="grid" x1={x(Math.log(t))} x2={x(Math.log(t))} y1={TOP - 6} y2={TOP + rows.length * ROW} />
		<text x={x(Math.log(t))} y={TOP - 10} text-anchor="middle" class="tick">{t}×</text>
	{/each}
	{#each rows as r, i (r.id)}
		{@const y = TOP + i * ROW}
		{@const x0 = x(0)}
		{@const x1 = x(Math.log(r.value))}
		<g>
			<title>{r.label}: {mult(r.value)}{r.note ? ` (${r.note})` : ''}</title>
			<rect x="0" y={y} width={W} height={ROW} fill="transparent" />
			<text x={LABEL - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label">{W < 520 && r.short ? r.short : r.label}</text>
			<rect x={Math.min(x0, x1)} y={y + 5} width={Math.max(1, Math.abs(x1 - x0))} height={ROW - 10} rx="2"
				fill={colour(r.party ?? r.id)} />
			<text x={W - RIGHT + 6} y={y + ROW / 2 + 4} class="value">{mult(r.value)}</text>
		</g>
	{/each}
</svg>
</div>

<style>
	.chart { width: 100%; max-width: 720px; }
	svg { display: block; max-width: 100%; height: auto; }
	.grid { stroke: var(--grid); }
	.grid.one { stroke: var(--text-3); }
	.tick { font-size: 11px; }
	.label { font-size: 13px; fill: var(--text); }
	.value { font-size: 12px; font-variant-numeric: tabular-nums; }
</style>
