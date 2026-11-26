import { BASES, DEFAULT_BASE } from '#lib/bases.js';
import { ogGet } from '#lib/server/og.js';

export const prerender = true;
export const entries = () => BASES.map((b) => ({ base: b === DEFAULT_BASE ? undefined : b }));
export const GET = ogGet('/[[base=base]]/party-vote');
