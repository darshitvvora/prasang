import { expect, it } from 'vitest';
import { ARTIST_SELF_KEYS, keys } from './queries';

it('creating/updating the artist profile refreshes the subscription (trial availability) and /me', () => {
  expect(ARTIST_SELF_KEYS).toContainEqual(keys.mySubscription);
  expect(ARTIST_SELF_KEYS).toContainEqual(keys.me);
  expect(ARTIST_SELF_KEYS).toContainEqual(['artists', 'me']);
});
