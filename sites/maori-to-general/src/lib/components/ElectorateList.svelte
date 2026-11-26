<script>
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, points, pct, candidateName } from '#lib/format.js';

	/** @type {{electorates: any[], names: Record<string, string>}} */
	let { electorates, names } = $props();

	let query = $state('');
	let flipsOnly = $state(false);
	let sortKey = $state('margin_pct');
	let ascending = $state(true);

	const columns = [
		{ key: 'name', label: 'Electorate' },
		{ key: 'prelim_winner', label: 'As counted' },
		{ key: 'winner', label: 'No Māori electorates' },
		{ key: 'prelim_margin_pct', label: 'Margin as counted', num: true },
		{ key: 'margin_pct', label: 'New margin', num: true },
		{ key: 'added_total', label: 'Māori-roll votes added', num: true },
		{ key: 'breakeven', label: 'Labour needs', num: true }
	];

	const rows = $derived.by(() => {
		const q = query.trim().toLowerCase();
		const value = (/** @type {any} */ e) => (sortKey === 'breakeven' ? e.breakeven ?? Infinity : e[sortKey]);
		return electorates
			.filter((e) => !flipsOnly || e.flips)
			.filter((e) => !q || e.name.toLowerCase().includes(q) ||
				e.winner.toLowerCase().includes(q) || e.prelim_winner.toLowerCase().includes(q))
			.toSorted((a, b) => {
				const va = value(a), vb = value(b);
				const c = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
				return ascending ? c : -c;
			});
	});

	/** @param {string} key */
	function sortBy(key) {
		if (sortKey === key) ascending = !ascending;
		else { sortKey = key; ascending = true; }
	}
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'independent');
	/** The share of Te Pāti Māori votes Labour needs, or why that doesn't apply. */
	const needs = (/** @type {number | null} */ b) =>
		b === null ? '—' : b <= 0 ? 'none' : b > 1 ? 'can’t' : pct(b, 0);
</script>

<div class="filters">
	<label>
		<span class="visually-hidden">Search</span>
		<input type="search" placeholder="Search electorate or candidate" bind:value={query} />
	</label>
	<label class="check"><input type="checkbox" bind:checked={flipsOnly} /> Only electorates that would flip</label>
</div>

<div class="table-wrap">
	<table>
		<thead>
			<tr>
				{#each columns as c (c.key)}
					<th class:num={c.num} aria-sort={sortKey === c.key ? (ascending ? 'ascending' : 'descending') : 'none'}>
						<button onclick={() => sortBy(c.key)}>
							{c.label}{sortKey === c.key ? (ascending ? ' ▲' : ' ▼') : ''}
						</button>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each rows as e (e.slug)}
				<tr>
					<td>
						<a href={link(`/electorate/${e.slug}/`)}>{e.name}</a>
						{#if e.flips}<span class="badge flip">would flip</span>{/if}
					</td>
					<td>
						<span class="swatch" style:background={colour(e.prelim_winner_party)}></span>{candidateName(e.prelim_winner)}
						<span class="muted small">{party(e.prelim_winner_party)}</span>
					</td>
					<td>
						<span class="swatch" style:background={colour(e.winner_party)}></span>{candidateName(e.winner)}
						<span class="muted small">{party(e.winner_party)}</span>
					</td>
					<td class="num" title="{votes(e.prelim_margin)} votes">{points(e.prelim_margin_pct)}</td>
					<td class="num" title="{votes(e.margin)} votes">{points(e.margin_pct)}</td>
					<td class="num">{votes(e.added_total)}</td>
					<td class="num">{needs(e.breakeven)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.filters { display: flex; flex-wrap: wrap; gap: 0.6em 1.2em; margin: 0.6em 0; align-items: center; }
	input[type='search'] {
		font: inherit; font-size: 0.9rem; padding: 0.3em 0.5em; border: 1px solid var(--border);
		border-radius: 4px; background: var(--surface); color: var(--text); width: 18em; max-width: 100%;
	}
	.check { font-size: 0.9rem; color: var(--text-2); }
	th button {
		font: inherit; font-weight: 600; color: inherit; background: none; border: 0; padding: 0;
		cursor: pointer; text-align: inherit;
	}
	.flip { color: var(--text); margin-left: 0.4em; }
	td:nth-child(2), td:nth-child(3) { min-width: 10em; }
	.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
