<script>
	// Map of the 2026 general electorates (2025 boundaries, clipped to land by
	// export_boundaries.py), coloured by leading party, with insets for the
	// cities. The Māori electorates aren't shown: in this scenario they don't exist.
	import { geoIdentity, geoPath } from 'd3-geo';
	import { feature } from 'topojson-client';
	import topo from '#lib/data/electorates-2025.topo.json';
	import { colour } from '#lib/parties.js';
	import { link } from '#lib/link.js';
	import { points, candidateName } from '#lib/format.js';

	/** @type {{electorates: any[], names: Record<string, string>, view: 'counted' | 'none'}} */
	let { electorates, names, view } = $props();

	const t = /** @type {any} */ (topo);
	const general = /** @type {any} */ (feature(t, t.objects.general)).features;

	// Inset areas in NZTM metres: [x0, y0, x1, y1].
	const INSETS = [
		{ name: 'Auckland', box: [1728000, 5888000, 1790000, 5950000] },
		{ name: 'Hamilton', box: [1783000, 5795000, 1817000, 5829000] },
		{ name: 'Wellington', box: [1733000, 5414000, 1785000, 5466000] },
		{ name: 'Christchurch', box: [1550000, 5160000, 1592000, 5202000] }
	];
	const boxFeature = (/** @type {number[]} */ [x0, y0, x1, y1]) => ({
		type: 'Feature', properties: {},
		geometry: { type: 'Polygon', coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] }
	});
	const projected = (/** @type {any} */ fit, w, h) => {
		const projection = /** @type {any} */ (geoIdentity().reflectY(true)).fitSize([w, h], fit);
		return { path: geoPath(projection), projection };
	};

	const MAIN_W = 300, MAIN_H = 420, INSET = 150;
	const main = projected({ type: 'FeatureCollection', features: general }, MAIN_W, MAIN_H);
	const insets = INSETS.map((i) => {
		const p = projected(boxFeature(i.box), INSET, INSET);
		const [[x0, y0], [x1, y1]] = main.path.bounds(boxFeature(i.box));
		const [bx0, by0, bx1, by1] = i.box;
		// Electorates whose bounding box (raw metres) overlaps the inset.
		const inBox = general.filter((/** @type {any} */ f) => {
			const [[fx0, fy0], [fx1, fy1]] = geoPath().bounds(f);
			return !(fx1 < bx0 || fx0 > bx1 || fy1 < by0 || fy0 > by1);
		});
		return { ...i, path: p.path, features: inBox, rect: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } };
	});

	const byName = $derived(Object.fromEntries(electorates.map((e) => [e.name, e])));
	function leader(/** @type {any} */ e) {
		if (!e) return null;
		return view === 'counted'
			? { party: e.prelim_winner_party, who: e.prelim_winner, margin: e.prelim_margin_pct }
			: { party: e.winner_party, who: e.winner, margin: e.margin_pct };
	}
	const fill = (/** @type {string} */ name) => colour(leader(byName[name])?.party);

	let hovered = $state(/** @type {string | null} */ (null));
	const hoveredInfo = $derived.by(() => {
		const e = hovered ? byName[hovered] : null;
		const l = leader(e);
		if (!e || !l) return null;
		const party = l.party ? names[l.party] ?? l.party : 'independent';
		return { name: e.name, text: ` ${candidateName(l.who)} (${party}) ${view === 'none' ? 'would win' : 'leads'} by ${points(l.margin)}${e.flips ? (view === 'none' ? ` · would flip from ${names[e.prelim_winner_party] ?? 'other'}` : ' · would flip without Māori electorates') : ''}` };
	});
	const parties = $derived(
		[...new Set(electorates.map((e) => leader(e)?.party))]
			.map((p) => ({ id: p, n: electorates.filter((e) => leader(e)?.party === p).length }))
			.sort((a, b) => b.n - a.n)
	);
	const hover = (/** @type {string} */ name) => ({
		onmouseenter: () => (hovered = name), onmouseleave: () => (hovered = null),
		onfocus: () => (hovered = name), onblur: () => (hovered = null)
	});
</script>

{#snippet shapes(/** @type {any[]} */ features, /** @type {any} */ path)}
	{#each features as f (f.properties.name)}
		{@const e = byName[f.properties.name]}
		<a href={link(`/electorate/${e?.slug}/`)} aria-label={f.properties.name} {...hover(f.properties.name)}>
			<path d={path(f)} fill={fill(f.properties.name)}>
				<title>{f.properties.name}</title>
			</path>
			{#if e?.flips}
				<!-- Hatched overlay: light stripes over the party colour. -->
				<path d={path(f)} class="hatch" fill="url(#flip-hatch)" />
			{/if}
		</a>
	{/each}
	<!-- The hover outline is drawn last, on top of every shape: SVG paints in
	     document order, so neighbours drawn later would otherwise cover the
	     outer half of its stroke. -->
	{@const h = hovered && features.find((/** @type {any} */ f) => f.properties.name === hovered)}
	{#if h}<path d={path(h)} class="hover-outline" />{/if}
{/snippet}

<figure>
	<p class="caption" class:idle={!hoveredInfo} aria-live="polite">{#if hoveredInfo}<span><strong>{hoveredInfo.name}:</strong>{hoveredInfo.text}</span>{:else}Hover over or tap an electorate.{/if}</p>
	<div class="maps">
		<div class="main">
			<svg viewBox="0 0 {MAIN_W} {MAIN_H}" role="img" aria-label="Map of general electorates by {view === 'counted' ? 'preliminary' : 'no-Māori-electorates'} leader">
				<defs>
					<pattern id="flip-hatch" patternUnits="userSpaceOnUse" width="3.5" height="3.5" patternTransform="rotate(45)">
						<rect width="1.6" height="3.5" class="hatch-stripe" />
					</pattern>
				</defs>
				{@render shapes(general, main.path)}
				{#each insets as i (i.name)}
					<rect class="inset-box" x={i.rect.x} y={i.rect.y} width={i.rect.w} height={i.rect.h} />
				{/each}
			</svg>
		</div>
		<div class="side">
			{#each insets as i, k (i.name)}
				<div class="inset">
					<svg viewBox="0 0 {INSET} {INSET}" role="img" aria-label="{i.name} electorates">
						<clipPath id="clip-{k}"><rect width={INSET} height={INSET} /></clipPath>
						<g clip-path="url(#clip-{k})">{@render shapes(i.features, i.path)}</g>
						<rect class="frame" width={INSET} height={INSET} />
					</svg>
					<span class="label small">{i.name}</span>
				</div>
			{/each}
		</div>
	</div>
	<ul class="legend small">
		{#each parties as p (p.id)}
			<li><span class="swatch" style:background={colour(p.id)}></span>{p.id ? names[p.id] ?? p.id : 'Other'} {p.n}</li>
		{/each}
		<li><span class="flip-key"></span>would flip</li>
	</ul>
</figure>

<style>
	figure { margin: 0; }
	.maps {
		display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
		grid-template-areas: 'main side'; gap: 0.8em; align-items: start;
	}
	.main { grid-area: main; }
	.side { grid-area: side; }
	@media (max-width: 700px) {
		.maps { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'main' 'side'; }
	}
	.side { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5em; }
	.inset { position: relative; }
	svg { width: 100%; display: block; height: auto; }
	path { stroke: var(--surface); stroke-width: 0.6; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
	path.hover-outline { fill: none; stroke: var(--highlight); stroke-width: 2; pointer-events: none; }
	path.hatch { stroke: none; pointer-events: none; }
	.hatch-stripe { fill: var(--surface); opacity: 0.6; }
	.inset-box { fill: none; stroke: var(--text-3); stroke-width: 0.8; vector-effect: non-scaling-stroke; }
	.frame { fill: none; stroke: var(--border); vector-effect: non-scaling-stroke; }
	.label { color: var(--text-2); }
	.caption {
		max-width: none; min-height: 2.6em; margin: 0.4em 0 0.8em; padding: 0.5em 0.8em;
		background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px; color: var(--text);
		display: flex; align-items: center;
	}
	.caption.idle { color: var(--text-2); }
	.caption strong { color: var(--text-2); }
	.legend { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.15em 0.9em; }
	.flip-key {
		display: inline-block; width: 0.8em; height: 0.8em; margin-right: 0.35em; vertical-align: -0.05em;
		background: var(--text-3); border-radius: 2px;
	}
	.flip-key {
		background: repeating-linear-gradient(-45deg, var(--text-3) 0 2px, color-mix(in srgb, var(--text-3) 40%, var(--surface)) 2px 4px);
	}
</style>
