<script>
	// Horizontal bars from 1 (no change) to each multiplier: above 1 means the
	// party did better among special votes than among ordinary votes. A row
	// with `domestic` and `overseas` values gets a pair of bars (domestic solid,
	// overseas a lighter tint with an outline); a row with `value`, one bar.
	import { scaleLinear } from 'd3-scale';
	import { colour } from '#lib/parties.js';
	import { mult } from '#lib/format.js';

	/** @typedef {{id: string, label: string, short?: string, party?: string | null, note?: string, value?: number, domestic?: number | null, overseas?: number | null}} Row */
	/** @type {{rows: Row[]}} */
	let { rows } = $props();

	const paired = $derived(rows.some((r) => r.domestic != null || r.overseas != null));
	const BAR = 14, GAP = 2;
	const ROW = $derived(paired ? 2 * BAR + GAP + 10 : 24);
	const RIGHT = 60;
	const TOP = $derived(paired ? 40 : 22);
	let width = $state(640);
	const W = $derived(Math.max(300, width));
	const LABEL = $derived(Math.min(160, Math.round(W * 0.3)));
	/** Each row's bars, top to bottom. */
	const bars = (/** @type {Row} */ r) =>
		paired
			? [
					{ kind: 'domestic', value: r.domestic ?? null },
					{ kind: 'overseas', value: r.overseas ?? null }
				]
			: [{ kind: 'single', value: r.value ?? null }];
	const values = $derived(rows.flatMap((r) => bars(r).map((b) => b.value)).filter((v) => v != null && v > 0));
	const ext = $derived(Math.max(...values.map((v) => Math.abs(Math.log(/** @type {number} */ (v))))));
	const lo = $derived(Math.min(0.5, Math.exp(-ext) * 0.95)), hi = $derived(Math.max(2, Math.exp(ext) * 1.05));
	// Log scale so 0.5 and 2 are the same distance from 1.
	const x = $derived(scaleLinear().domain([Math.log(lo), Math.log(hi)]).range([LABEL, W - RIGHT]));
	const ticks = $derived([0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4].filter((t) => t >= lo && t <= hi));
	const title = (/** @type {Row} */ r) =>
		paired
			? `${r.label}: domestic ${r.domestic == null ? '—' : mult(r.domestic)}, overseas ${r.overseas == null ? '—' : mult(r.overseas)}`
			: `${r.label}: ${r.value == null ? '—' : mult(r.value)}${r.note ? ` (${r.note})` : ''}`;
</script>

<div class="chart" bind:clientWidth={width}>
<svg width={W} viewBox="0 0 {W} {TOP + rows.length * ROW + 6}" role="img"
	aria-label={paired ? 'Domestic and overseas special-vote multipliers by party' : 'Special-vote multiplier by party'}>
	{#if paired}
		<g class="legend">
			<rect x={LABEL} y="2" width="14" height="10" rx="2" class="swatch-domestic" />
			<text x={LABEL + 19} y="11">Domestic specials</text>
			<rect x={LABEL + 140} y="2" width="14" height="10" rx="2" class="swatch-overseas" />
			<text x={LABEL + 159} y="11">Overseas specials</text>
		</g>
	{/if}
	{#each ticks as t (t)}
		<line class:one={t === 1} class="grid" x1={x(Math.log(t))} x2={x(Math.log(t))} y1={TOP - 6} y2={TOP + rows.length * ROW} />
		<text x={x(Math.log(t))} y={TOP - 10} text-anchor="middle" class="tick">{t}×</text>
	{/each}
	{#each rows as r, i (r.id)}
		{@const y = TOP + i * ROW}
		{@const x0 = x(0)}
		{@const fill = colour(r.party ?? r.id)}
		<g>
			<title>{title(r)}</title>
			<rect x="0" y={y} width={W} height={ROW} fill="transparent" />
			<text x={LABEL - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label">{W < 520 && r.short ? r.short : r.label}</text>
			{#each bars(r) as b, j (b.kind)}
				{@const by = paired ? y + 5 + j * (BAR + GAP) : y + 5}
				{@const h = paired ? BAR : ROW - 10}
				{#if b.value != null && b.value > 0}
					{@const x1 = x(Math.log(b.value))}
					<rect x={Math.min(x0, x1)} y={by} width={Math.max(1, Math.abs(x1 - x0))} height={h} rx="2"
						fill={fill} class:overseas={b.kind === 'overseas'} style:--c={fill} />
				{/if}
				<text x={W - RIGHT + 6} y={by + h / 2 + 4} class="value" class:small={paired}>
					{b.value == null ? '—' : mult(b.value)}
				</text>
			{/each}
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
	.value.small { font-size: 11px; }
	/* Overseas: a light tint of the party colour, outlined in it. */
	rect.overseas { fill: color-mix(in srgb, var(--c) 30%, var(--surface)); stroke: var(--c); stroke-width: 1; }
	.legend text { font-size: 11px; fill: var(--text-2); }
	.swatch-domestic { fill: var(--text-2); }
	.swatch-overseas { fill: color-mix(in srgb, var(--text-2) 30%, var(--surface)); stroke: var(--text-2); }
</style>
