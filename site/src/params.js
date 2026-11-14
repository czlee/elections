import { defineParams } from '@sveltejs/kit/params';
import { OTHER_BASES } from '#lib/bases.js';

export const params = defineParams({
	/** The optional [[base]] route segment: a base year other than the default. */
	base: (param) => (OTHER_BASES.includes(param) ? param : undefined)
});
