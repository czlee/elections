<script>
	import { link } from '#lib/link.js';
	import { colour } from '#lib/parties.js';
	import { votes, pct, mult, candidateName } from '#lib/format.js';

	/** @type {{electorates: any[], names: Record<string, string>}} */
	let { electorates, names } = $props();

	let query = $state('');
	let roll = $state('all');
	let sortKey = $state('margin_pct');
	let ascending = $state(true);

	const columns = [
		{ key: 'name', label: 'Electorate' },
		{ key: 'winner', label: 'Projected winner' },
		{ key: 'second', label: 'Runner-up' },
		{ key: 'prelim_margin_pct', label: 'Prelim margin', num: true },
		{ key: 'margin_pct', label: 'Projected margin', num: true },
		{ key: 'gap', label: 'Needs / had', num: true }
	];

	const rows = $derived.by(() => {
		const q = query.trim().toLowerCase();
		const value = (/** @type {any} */ e) =>
			e.omitted ? Infinity
				: sortKey === 'gap' ? (e.breakeven.needed ?? Infinity) / e.breakeven.had
				: e[sortKey];
		return electorates
			.filter((e) => roll === 'all' || e.roll === roll)
			.filter((e) => !q || e.name.toLowerCase().includes(q) ||
				(e.winner ?? '').toLowerCase().includes(q) || (e.second ?? '').toLowerCase().includes(q))
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
	const party = (/** @type {string | null} */ p) => (p ? names[p] ?? p : 'Ind./other');
</script>

<div class="filters">
	<label>
		<span class="visually-hidden">Search</span>
		<input type="search" placeholder="Search electorate or candidate" bind:value={query} />
	</label>
	<label>
		<span class="visually-hidden">Roll</span>
		<select bind:value={roll}>
			<option value="all">All 71 electorates</option>
			<option value="general">General (64)</option>
			<option value="maori">Māori (7)</option>
		</select>
	</label>
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
						{#if e.flips}<span class="badge flip">flips</span>{/if}
					</td>
					{#if e.omitted}
						<td colspan="5" class="muted">
							Not projected (no 2023 electorate vote): preliminary leader
							{candidateName(e.winner_label.replace(/ \(.*\)$/, ''))}
						</td>
					{:else}
						<td>
							<span class="swatch" style:background={colour(e.winner_party)}></span>{candidateName(e.winner)}
							<span class="muted small">{party(e.winner_party)}</span>
						</td>
						<td>
							<span class="swatch" style:background={colour(e.second_party)}></span>{candidateName(e.second)}
							<span class="muted small">{party(e.second_party)}</span>
						</td>
						<td class="num" title="{votes(e.prelim_margin)} votes">
							{pct(e.prelim_margin_pct)}
							{#if e.flips}<span class="muted small">({party(e.prelim_winner_party)})</span>{/if}
						</td>
						<td class="num" title="{votes(e.margin)} votes">{pct(e.margin_pct)}</td>
						<td class="num">
							{e.breakeven.needed === null ? '—' : mult(e.breakeven.needed)}
							<span class="muted">/ {mult(e.breakeven.had)}</span>
						</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.filters { display: flex; flex-wrap: wrap; gap: 0.6em; margin: 0.6em 0; }
	input, select {
		font: inherit; font-size: 0.9rem; padding: 0.3em 0.5em; border: 1px solid var(--border);
		border-radius: 4px; background: var(--surface); color: var(--text);
	}
	input { width: 16em; max-width: 100%; }
	th button {
		font: inherit; font-weight: 600; color: inherit; background: none; border: 0; padding: 0;
		cursor: pointer; text-align: inherit;
	}
	.flip { color: var(--text); margin-left: 0.4em; }
	td:nth-child(2), td:nth-child(3) { min-width: 10em; }
	.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
