import { baseOf } from '#lib/bases.js';
import { national } from '#lib/server/data.js';

export function load({ params }) {
	return { national: national(baseOf(params.base)) };
}
