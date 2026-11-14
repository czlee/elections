<script>
	import ElectorateList from '#lib/components/ElectorateList.svelte';
	import Term from '#lib/components/Term.svelte';

	let { data } = $props();
	const names = $derived(Object.fromEntries(data.parties.map((p) => [p.id, p.short])));
</script>

<svelte:head><title>Electorates · 2026 special votes</title></svelte:head>

<h1>Electorates</h1>
<p class="muted small">
	“Needs” is the special-vote
	<Term tip="How they did in the special votes compared with the preliminary count: share of specials ÷ share of preliminary votes. Above 1, specials helped.">multiplier</Term>
	the projected runner-up would have needed to tie, against the one they got from 2023. Click an
	electorate for its working.
</p>
<ElectorateList electorates={data.electorates} {names} />
