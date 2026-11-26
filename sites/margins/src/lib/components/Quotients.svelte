<script>
	import { colour } from '#lib/parties.js';
	import { votes as fmtVotes } from '#lib/format.js';

	/** @type {{data: any}} */
	let { data } = $props();
	const parties = $derived(data.parties.filter((/** @type {any} */ p) => p.qualified));
	const lastAllocated = $derived(data.ladder.findLast((/** @type {any} */ r) => r.allocated)?.rank);
	const first = $derived(data.to_allocate);

	/** A quotient is a party's nth seat; the divisor is 2n − 1. */
	const seatOf = (/** @type {number} */ divisor) => (divisor + 1) / 2;
	const keyOf = (/** @type {string} */ party, /** @type {number} */ seat) => `${party}|${seat}`;
	/** Whether the ranking's row is the one that last got in, or first missed out. */
	const isPick = (/** @type {any} */ r) => r.rank === first || r.rank === first + 1;
	/** Whether a party's last-in or next-out quotient is the last one in or first one out of the whole House. */
	const pickedCell = (/** @type {any} */ p, /** @type {'last' | 'next'} */ which) => {
		const q = p[which];
		if (!q) return false;
		const r = data.ladder.find((/** @type {any} */ r) => r.rank === first + (which === 'last' ? 0 : 1));
		return !!r && r.party === p.party && r.seat === seatOf(q.divisor);
	};

	/** Every party's last-in and next-out quotients: the other rows of the ranking are faded. */
	const relevant = $derived(
		new Set(
			parties.flatMap((/** @type {any} */ p) =>
				['last', 'next'].filter((w) => p[w]).map((w) => keyOf(p.party, seatOf(p[w].divisor)))
			)
		)
	);

	/** Key of the quotient under the pointer, in either table, so the other table can show it too. */
	let hovered = $state('');
</script>

<p class="muted">
	A party’s nth seat has quotient votes ÷ (2n − 1). The {data.to_allocate} highest quotients get the Sainte-Laguë seats
	({data.total_seats}, less electorates won by independents or parties without a list). The {data.to_allocate}th is the last seat in and
	the {data.to_allocate + 1}th the first one out. Each party’s last seat in and next seat out are on the left; the ranking around the
	cutoff is on the right.
</p>
<div class="pair">
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Party</th><th class="num">Party votes</th><th class="num">Seats</th>
					<th class="num">Last in</th><th class="num">÷</th><th class="num">Next out</th><th class="num">÷</th>
				</tr>
			</thead>
			<tbody>
				{#each parties as p (p.party)}
					<tr>
						<td><span class="swatch" style:background={colour(p.id)}></span>{p.name}</td>
						<td class="num">{fmtVotes(p.votes)}</td>
						<td class="num">{p.entitlement}</td>
						{#each ['last', 'next'] as which (which)}
							{@const q = p[which]}
							{#if q}
								{@const k = keyOf(p.party, seatOf(q.divisor))}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<td class="num q" class:pick={pickedCell(p, /** @type {any} */ (which))} class:linked={hovered === k}
									onmouseenter={() => (hovered = k)} onmouseleave={() => (hovered = '')}>{fmtVotes(q.quotient)}</td>
								<td class="num muted">{q.divisor}</td>
							{:else}
								<td class="num">–</td><td class="num">–</td>
							{/if}
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	<div class="table-wrap">
		<table>
			<thead>
				<tr><th class="num">Rank</th><th>Party</th><th class="num">Its seat</th><th class="num muted">÷</th><th class="num">Quotient</th></tr>
			</thead>
			<tbody onmouseleave={() => (hovered = '')} role="presentation">
				{#each data.ladder as r (r.rank)}
					{@const k = keyOf(r.party, r.seat)}
					<tr class:faded={!relevant.has(k)} class:pick={isPick(r)} class:linked={hovered === k} class:cut={r.rank === lastAllocated}
						onmouseenter={() => (hovered = k)}>
						<td class="num">{r.rank}</td>
						<td><span class="swatch" style:background={colour(r.id)}></span>{r.name}</td>
						<td class="num">{r.seat}</td>
						<td class="num muted">{2 * r.seat - 1}</td>
						<td class="num">{fmtVotes(r.quotient)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<style>
	.pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 0 2em; align-items: start; }
	/* The last quotient in and the first one out. */
	.pick { background: color-mix(in srgb, var(--highlight) 32%, transparent); font-weight: 600; }
	tr.faded td { color: var(--text-3); opacity: 0.6; }
	tr.faded.linked td { opacity: 1; }
	/* The quotient under the pointer, or its counterpart in the other table. */
	.linked { box-shadow: inset 0 0 0 2px var(--accent); }
	tr.linked { background: var(--surface-2); }
	tr.cut td { border-bottom: 2px solid var(--text-2); }
	td.q { cursor: default; }
</style>
