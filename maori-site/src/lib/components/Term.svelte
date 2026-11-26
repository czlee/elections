<script>
	// A term with a definition that shows on hover, keyboard focus, or tap. The tooltip
	// is kept inside the viewport and drops below the term if there's no room above.
	/** @type {{ tip: string, children: import('svelte').Snippet }} */
	let { tip, children } = $props();
	const id = $props.id();
	let open = $state(false);
	/** @type {HTMLButtonElement | undefined} */
	let trigger = $state();
	/** @type {HTMLSpanElement | undefined} */
	let box = $state();
	let shift = $state(0);
	let below = $state(false);

	$effect(() => {
		if (!open || !trigger || !box) return;
		const t = trigger.getBoundingClientRect();
		const w = box.offsetWidth;
		const margin = 8;
		const centre = t.left + t.width / 2;
		const left = Math.min(Math.max(centre - w / 2, margin), innerWidth - margin - w);
		shift = left - (centre - w / 2);
		below = t.top < box.offsetHeight + 12;

		const close = (/** @type {Event} */ ev) => {
			if (ev instanceof KeyboardEvent ? ev.key === 'Escape' : !trigger?.contains(/** @type {Node} */ (ev.target)))
				open = false;
		};
		addEventListener('pointerdown', close);
		addEventListener('keydown', close);
		addEventListener('scroll', close, { passive: true });
		return () => {
			removeEventListener('pointerdown', close);
			removeEventListener('keydown', close);
			removeEventListener('scroll', close);
		};
	});
</script>

<span class="wrap"><button
		type="button"
		class="term"
		aria-describedby={id}
		bind:this={trigger}
		onclick={() => (open = true)}
		onmouseenter={() => (open = true)}
		onmouseleave={() => (open = false)}
		onfocus={() => (open = true)}
		onblur={() => (open = false)}>{@render children()}</button><span
		{id}
		role="tooltip"
		class="tip"
		class:open
		class:below
		bind:this={box}
		style:--shift="{shift}px">{tip}</span></span>

<style>
	.wrap { position: relative; }
	.term {
		font: inherit; color: inherit; background: none; border: 0; padding: 0; margin: 0;
		text-decoration: underline dotted; text-underline-offset: 0.2em; cursor: help;
	}
	.tip {
		/* display: none when closed, so the hidden box can't widen the page on phones. */
		display: none; position: absolute; left: 50%; bottom: calc(100% + 6px); z-index: 10;
		transform: translateX(calc(-50% + var(--shift, 0px)));
		width: max-content; max-width: min(18em, calc(100vw - 16px)); padding: 0.45em 0.65em;
		border: 1px solid var(--border); border-radius: 6px; background: var(--surface-2); color: var(--text);
		font-size: 0.85rem; font-weight: 400; line-height: 1.35; text-align: left; white-space: normal;
		box-shadow: 0 2px 8px rgb(0 0 0 / 0.15);
	}
	.tip.open { display: block; }
	.tip.below { bottom: auto; top: calc(100% + 6px); }
</style>
