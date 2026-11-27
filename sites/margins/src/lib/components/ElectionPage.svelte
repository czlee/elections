<script>
	import PartyVote from '#lib/components/PartyVote.svelte';
	import Quotients from '#lib/components/Quotients.svelte';
	import Closest from '#lib/components/Closest.svelte';
	import { ELECTIONS, electionPath } from '#lib/elections.js';
	import { resolve } from '$app/paths';

	/** @type {{election: {year: string, prelim: boolean, official: string}, data: any}} */
	let { election: e, data: d } = $props();

	/** The final results for this preliminary count's election, if they're published. */
	const final = $derived(e.prelim ? ELECTIONS.find((x) => x.year === e.year && !x.prelim) : undefined);
</script>

<h1>{e.year} New Zealand election margins{e.prelim ? ', preliminary count' : ''}</h1>
<p class="muted">
	From the Electoral Commission’s <a href={e.official} target="electionresults" rel="noopener">{e.prelim ? 'preliminary ' : ''}results</a>.
</p>

{#if final}
	<div class="alert" role="status">
		<strong>The final results are out.</strong>
		This page shows the preliminary count, which has been superseded.
		<a href={resolve(/** @type {any} */ (electionPath(final.id)))}>See the final {final.year} results</a>.
	</div>
{/if}

<h2>Party vote: votes to gain or lose a seat</h2>
<PartyVote data={d} />

<h2>Sainte-Laguë quotients</h2>
<Quotients data={d} />

<h2>Closest electorates</h2>
<Closest data={d} official={e.official} />

<style>
	.alert {
		margin: 1rem 0;
		padding: 0.75rem 1rem;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-left: 4px solid var(--accent);
		border-radius: 4px;
	}
</style>
