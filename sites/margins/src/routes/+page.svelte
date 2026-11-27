<script>
	import ElectionPage from '#lib/components/ElectionPage.svelte';

	/** @type {{data: {election: {year: string, prelim: boolean, official: string}, data: any}}} */
	let { data: pageData } = $props();
</script>

<ElectionPage election={pageData.election} data={pageData.data} />
