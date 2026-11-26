import { DEFAULT_BASE } from '#lib/bases.js';
import { electorateBases } from '#lib/server/data.js';
import { ogGet } from '#lib/server/og.js';

export const prerender = true;
export const entries = () => electorateBases.map((b) => ({ base: b === DEFAULT_BASE ? undefined : b }));
export const GET = ogGet('/[[base=base]]/electorates');
