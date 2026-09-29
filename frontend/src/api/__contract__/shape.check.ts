// Self-test for check(): each @ts-expect-error line must stay an error.
import { check } from './shape';

interface Sample { id: string; nested: { a: number; b: string | null }; list: { x: boolean }[] }

check<Sample>()({ id: 'ok', nested: { a: 1, b: null }, list: [{ x: true }] });
// @ts-expect-error missing top-level key
check<Sample>()({ nested: { a: 1, b: null }, list: [] });
// @ts-expect-error extra nested key
check<Sample>()({ id: 'x', nested: { a: 1, b: 'y', c: 2 }, list: [] });
// @ts-expect-error misspelled key inside array item
check<Sample>()({ id: 'x', nested: { a: 1, b: null }, list: [{ y: true }] });

// Non-fresh values (like JSON imports) skip TS excess-property checks; NoExtraKeys must catch them.
const withExtra = { id: 'x', nested: { a: 1, b: null, extra: 1 }, list: [] };
// @ts-expect-error extra key on a non-fresh value
check<Sample>()(withExtra);
