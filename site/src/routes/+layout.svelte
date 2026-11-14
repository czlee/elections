<script>
	// DM Sans, self-hosted via Fontsource (SIL Open Font License); latin and latin-ext subsets.
	import '@fontsource/dm-sans/400.css';
	import '@fontsource/dm-sans/500.css';
	import '@fontsource/dm-sans/600.css';
	import '@fontsource/dm-sans/700.css';
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import appleTouchIcon from '#lib/assets/apple-touch-icon.png';
	import { DRAFT } from '#lib/config.js';
	import { link } from '#lib/link.js';
	import { page } from '$app/state';
	import { BOUNDARIES } from '#lib/bases.js';

	/** @type {{children: import('svelte').Snippet, data: any}} */
	let { children, data } = $props();

	const R = '/[[base=base]]';
	const nav = $derived([
		{ href: '/', route: R, label: 'Projection' },
		{ href: '/party-vote/', route: `${R}/party-vote`, label: 'Party vote' },
		...(data.hasElectorates ? [{ href: '/electorates/', route: `${R}/electorates`, label: 'Electorates' }] : [])
	]);
	/** This page under another base year, or that base's landing page if it has no such page. */
	function switchTo(/** @type {{base: string, hasElectorates: boolean}} */ b) {
		const route = page.route.id ?? R;
		if (route === `${R}/party-vote`) return link('/party-vote/', b.base);
		if (!b.hasElectorates) return link('/', b.base);
		if (route === `${R}/electorates`) return link('/electorates/', b.base);
		if (route === `${R}/electorate/[slug]`) return link(`/electorate/${page.params.slug}/`, b.base);
		return link('/', b.base);
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} type="image/svg+xml" />
	<link rel="apple-touch-icon" href={appleTouchIcon} />
	{#if DRAFT}<meta name="robots" content="noindex, nofollow" />{/if}
	<title>{data.meta.title}</title>
	<meta name="description" content={data.meta.description} />
	<link rel="canonical" href={data.meta.url} />
	<meta property="og:type" content="website" />
	<meta property="og:locale" content="en_NZ" />
	<meta property="og:site_name" content={data.meta.siteName} />
	<meta property="og:title" content={data.meta.title} />
	<meta property="og:description" content={data.meta.description} />
	<meta property="og:url" content={data.meta.url} />
	<meta property="og:image" content={data.meta.image} />
	<meta property="og:image:type" content="image/png" />
	<meta property="og:image:width" content={String(data.meta.imageWidth)} />
	<meta property="og:image:height" content={String(data.meta.imageHeight)} />
	<meta property="og:image:alt" content={data.meta.description} />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

{#if DRAFT}
	<div class="draft-banner" role="note">
		<strong>DRAFT</strong> · Work in progress: numbers, wording and layout may change. Not an official result.
	</div>
{/if}

<header>
	<nav>
		<a class="brand" href={link('/')}>2026 special votes projection{#if DRAFT}<span class="draft-tag">DRAFT</span>{/if}</a>
		{#each nav as item (item.href)}
			<a href={link(item.href)} aria-current={page.route.id === item.route ? 'page' : undefined}
				>{item.label}</a
			>
		{/each}
		<span class="bases" role="group" aria-label="Base year">
			<span class="bases-label">Using specials from</span>
			{#each data.bases as b (b.base)}
				<a href={switchTo(b)} aria-current={b.base === data.base ? 'true' : undefined}>{b.base}</a>
			{/each}
		</span>
	</nav>
</header>

<main>
	{@render children()}
</main>

<footer>
	<p>
		Projection by Chuan-Zheng Lee. Not an official result. Based on {data.base}’s special votes; see the
		<a href={link('/#limitations')}>limitations</a>.
	</p>
	<p>
		The method and design decisions are mine; the code, including the data processing and this
		website, was largely written by <a href="https://claude.ai/">Claude</a>, under my
		direction.
	</p>
	<p>
		Data: <a href="https://www.electionresults.govt.nz/">Electoral Commission</a> ({data.base} and 2026
		results), <a href="https://web.archive.org/">Internet Archive</a> ({data.base} preliminary count){#if data.hasElectorates},
			<a href="https://datafinder.stats.govt.nz/">Stats NZ</a> (2023 Census electoral population,
			{BOUNDARIES[data.base]} and 2025 electorate boundaries, and 2025 regional council boundaries
			for the coastline, CC BY 4.0){/if}. Code:
		<a href="https://github.com/czlee/elections">czlee/elections</a>.
	</p>
</footer>

<style>
	header { border-bottom: 1px solid var(--border); }
	.draft-banner {
		background: #fab219; color: #1a1a19; font-size: 0.85rem; text-align: center; padding: 0.35em 16px;
	}
	.draft-tag {
		font-size: 0.65rem; font-weight: 700; letter-spacing: 0.05em; vertical-align: 0.2em; margin-left: 0.5em;
		padding: 0.1em 0.4em; border-radius: 3px; background: #fab219; color: #1a1a19;
	}
	nav, main, footer { max-width: 1040px; margin: 0 auto; padding: 0 16px; }
	nav { display: flex; flex-wrap: wrap; gap: 0.3em 1.2em; align-items: baseline; padding-block: 0.7em; }
	nav a { color: var(--text-2); text-decoration: none; }
	nav a[aria-current='page'] { color: var(--text); font-weight: 600; }
	nav .brand { color: var(--text); font-weight: 700; margin-right: auto; }
	.bases {
		display: inline-flex; gap: 0.15em; align-items: baseline; font-size: 0.85rem;
		margin-left: 0.2em; padding-left: 1em; border-left: 1px solid var(--border);
	}
	.bases-label { color: var(--text-3); margin-right: 0.35em; }
	.bases a { padding: 0.05em 0.4em; border-radius: 4px; border: 1px solid transparent; }
	.bases a[aria-current='true'] { color: var(--text); font-weight: 600; border-color: var(--border); }
	main { padding-bottom: 3em; }
	footer { border-top: 1px solid var(--border); color: var(--text-3); font-size: 0.8rem; padding-block: 1em 2em; }
	footer a { color: var(--text-2); }
</style>
