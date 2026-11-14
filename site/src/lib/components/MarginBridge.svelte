<script>
	// Waterfall of the projected winner's lead over the projected runner-up:
	// preliminary lead, + the winner's specials, − the runner-up's specials,
	// = projected margin. Positive means the projected winner is ahead.
	import { scaleLinear } from 'd3-scale';
	import { colour } from '#lib/parties.js';
	import { signed } from '#lib/format.js';

	/** @type {{lead: number, plus: number, minus: number, winner: string, second: string, winnerParty: string | null, secondParty: string | null}} */
	let { lead, plus, minus, winner, second, winnerParty, secondParty } = $props();

	const ROW = 34, RIGHT = 70, TOP = 8;
	let width = $state(640);
	const W = $derived(Math.max(300, width));
	const LABEL = $derived(Math.min(210, Math.round(W * 0.36)));
	// Surnames only on narrow screens or for long names.
	const short = (/** @type {string} */ n) => (W < 520 || n.length > 16 ? n.split(' ').at(-1) : n);
	const steps = $derived([
		{ label: 'Preliminary lead', from: 0, to: lead, fill: 'var(--text-3)' },
		{ label: `+ ${short(winner)}’s specials`, from: lead, to: lead + plus, fill: colour(winnerParty) },
		{ label: `− ${short(second)}’s specials`, from: lead + plus, to: lead + plus - minus, fill: colour(secondParty) },
		{ label: 'Projected margin', from: 0, to: lead + plus - minus, fill: 'var(--text)' }
	]);
	const all = $derived(steps.flatMap((s) => [s.from, s.to]));
	const x = $derived(scaleLinear().domain([Math.min(0, ...all), Math.max(0, ...all)]).range([LABEL, W - RIGHT]).nice());
</script>

<div class="chart" bind:clientWidth={width}>
<svg width={W} viewBox="0 0 {W} {TOP + steps.length * ROW + 4}" role="img"
	aria-label="Margin: preliminary lead {signed(lead)}, plus {signed(plus)}, minus {signed(minus)}, projected {signed(lead + plus - minus)}">
	<line class="zero" x1={x(0)} x2={x(0)} y1={TOP} y2={TOP + steps.length * ROW} />
	{#each steps as s, i (i)}
		{@const y = TOP + i * ROW}
		<g>
			<title>{s.label}: {signed(s.to - s.from)}</title>
			<text x={LABEL - 8} y={y + ROW / 2 + 4} text-anchor="end" class="label" class:strong={i === 3}>{s.label}</text>
			<rect x={Math.min(x(s.from), x(s.to))} y={y + 7} width={Math.max(1.5, Math.abs(x(s.to) - x(s.from)))}
				height={ROW - 14} rx="2" fill={s.fill} />
			{#if i < steps.length - 1}
				<line class="link" x1={x(s.to)} x2={x(s.to)} y1={y + ROW - 7} y2={y + ROW + 7} />
			{/if}
			<text x={Math.max(x(s.from), x(s.to)) + 6} y={y + ROW / 2 + 4} class="value">
				{i === 0 || i === 3 ? signed(s.to) : signed(s.to - s.from)}
			</text>
		</g>
	{/each}
</svg>
</div>

<style>
	.chart { width: 100%; max-width: 720px; }
	svg { display: block; max-width: 100%; height: auto; }
	.zero { stroke: var(--text-3); }
	.link { stroke: var(--text-3); stroke-dasharray: 2 2; }
	.label { font-size: 13px; fill: var(--text); }
	.label.strong { font-weight: 700; }
	.value { font-size: 12px; font-variant-numeric: tabular-nums; }
</style>
