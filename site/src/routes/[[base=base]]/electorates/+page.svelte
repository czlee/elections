<script>
	import ElectorateList from '#lib/components/ElectorateList.svelte';
	import Term from '#lib/components/Term.svelte';

	let { data } = $props();
	const names = $derived(Object.fromEntries(data.parties.map((p) => [p.id, p.short])));
</script>

<h1>Electorates</h1>
<p class="muted small">
	“Specials needed” is how much better the projected runner-up would have needed to do in the
	special votes to tie, with everyone else’s
	<Term tip="How a party did in the special votes compared with ordinary votes: share of specials ÷ share of ordinary votes, separately for overseas and domestic special votes. Above 1, specials helped.">multipliers</Term>
	unchanged (“—” if even every special vote wouldn’t be enough). Click an electorate for its working.
</p>
<ElectorateList electorates={data.electorates} {names} />
