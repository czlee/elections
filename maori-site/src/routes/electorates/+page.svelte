<script>
	import ElectorateList from '#lib/components/ElectorateList.svelte';
	import Term from '#lib/components/Term.svelte';

	let { data } = $props();
	const names = $derived(Object.fromEntries(data.parties.map((/** @type {any} */ p) => [p.id, p.short])));
</script>

<h1>General electorates</h1>
<p class="muted small">
	“Labour needs” is the
	<Term tip="The share of the electorate’s Te Pāti Māori Māori-roll votes that would have to go to Labour (the rest not voting for anyone) for Labour’s candidate to tie with the strongest rival, with everything else as in the main analysis. “none”: Labour wins even if none of them do. “can’t”: Labour doesn’t win even if all of them do.">share of Te Pāti Māori voters</Term>
	who would have to vote Labour for Labour to win the seat. Click an electorate for its working.
</p>
<ElectorateList electorates={data.electorates} {names} />
