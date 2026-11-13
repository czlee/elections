<script>
	import { link } from '#lib/link.js';
</script>

<svelte:head>
	<title>Method · 2026 special votes projection</title>
</svelte:head>

<h1>Method</h1>
<p>
	The 2026 preliminary count leaves out special votes, about 400,000 of them. This projects the final
	result by assuming each party (and each party's candidate) does as well among 2026 special voters,
	relative to its preliminary result, as it did in 2023. Nothing else is modelled.
</p>

<h2>Party vote</h2>
<ol>
	<li>For each party, the 2023 <strong>multiplier</strong> is its share of 2023 special votes divided by its share of the 2023 preliminary count. "Special votes" means final minus preliminary valid votes, which also includes official-count corrections to ordinary votes.</li>
	<li>The number of 2026 specials is the Electoral Commission's estimate (399,365) times 2023's ratio of actual special party votes to its estimate (596,770 / 567,000 = 1.0525).</li>
	<li>Each 2026 party's share of the specials is its preliminary share times its multiplier, normalised to 100%. New parties get 1; parties that were part of an umbrella party in 2023 (e.g. Freedoms NZ) use its multiplier.</li>
	<li>Seats: Sainte-Laguë over 120 seats among parties with 5% or an electorate, plus overhang. The allocation code reproduces the official 2017, 2023 and 2026-preliminary allocations.</li>
</ol>
<p><a href={link('/party-vote/')}>Party vote working →</a></p>

<h2>Electorates</h2>
<ol>
	<li><strong>Notional 2023 results on 2025 boundaries.</strong> Each 2026 electorate's 2023 preliminary and final counts are weighted sums of the 2023 electorates that overlap it, weighted by 2023 Census electoral population by 2025 meshblock. This assumes votes are spread evenly over each 2023 electorate's population.</li>
	<li><strong>Multipliers</strong> as nationally, but from the notional counts, separately for party and electorate votes. Candidates are matched by party. A candidate whose party had no 2023 candidate in the area uses the party's party-vote multiplier there; independents get 1.</li>
	<li><strong>Volume.</strong> Each electorate's specials are its preliminary count times its notional 2023 ratio of specials to preliminary votes, times one national factor so the party votes add up to the national projection.</li>
	<li>Port Waikato is not projected: 2023 had no general-election electorate vote there.</li>
</ol>

<h2>Limitations</h2>
<ul>
	<li>Same-day enrolment and enrolment changes while voting no longer count as special votes in 2026, which reportedly cut specials by about 30%. The 2023 mix of special voters may not carry over.</li>
	<li>When a 2023 party has no candidate in 2026, its special votes are effectively shared among everyone else in proportion, though in reality they'd lean to particular parties.</li>
	<li>Population weights stand in for enrolled electors (and, for Māori electorates, for the Māori roll).</li>
	<li>The 2023 preliminary count comes from Wayback Machine captures of the results site; all but Port Waikato's were archived.</li>
	<li>It's a mechanical projection, not a forecast: no uncertainty ranges.</li>
</ul>
<p class="small muted">
	Full notes and code: <a href="https://github.com/czlee/elections">github.com/czlee/elections</a>
	(<code>project_specials.py</code>, <code>project_electorates.py</code>, <code>NOTES.md</code>).
</p>
