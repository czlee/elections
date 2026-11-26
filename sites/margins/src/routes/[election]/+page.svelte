<script>
	import PartyVote from '#lib/components/PartyVote.svelte';
	import Quotients from '#lib/components/Quotients.svelte';
	import Closest from '#lib/components/Closest.svelte';

	/** @type {{data: {election: {year: string, prelim: boolean, official: string}, data: any}}} */
	let { data: pageData } = $props();
	const e = $derived(pageData.election);
	const d = $derived(pageData.data);
</script>

<svelte:head>
	<title>{e.year} New Zealand election margins{e.prelim ? ' (preliminary)' : ''}</title>
	<meta name="description" content="How many party votes it would take for each party to gain or lose a seat at the {e.year} New Zealand general election, and the closest electorates." />
</svelte:head>

<h1>{e.year} New Zealand election margins{e.prelim ? ', preliminary count' : ''}</h1>
<p class="muted">
	From the Electoral Commission’s <a href={e.official} target="electionresults" rel="noopener">{e.prelim ? 'preliminary ' : ''}results</a>.
</p>

<h2>Party vote: votes to gain or lose a seat</h2>
<PartyVote data={d} />

<h2>Sainte-Laguë quotients</h2>
<Quotients data={d} />

<h2>Closest electorates</h2>
<Closest data={d} official={e.official} />
