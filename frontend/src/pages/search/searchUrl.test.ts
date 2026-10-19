import { describe, expect, it } from 'vitest';
import { MAX_PRICE, parseSearch, toSearchString, activeFilterCount } from './searchUrl';

describe('parseSearch', () => {
  it('defaults city to Mumbai, sort to relevance, page 1', () => {
    expect(parseSearch(new URLSearchParams(''))).toEqual({ city: 'Mumbai', sort: 'relevance', page: 1 });
  });

  it('reads every filter with the right types', () => {
    const p = parseSearch(new URLSearchParams(
      'q=magic&city=Pune&area=Wakad&artistType=dj&eventType=wedding&language=Hindi&readyToTravel=true&minPrice=5000&maxPrice=40000&minRating=4.5&verifiedOnly=true&featuredOnly=true&sort=rating&page=3'));
    expect(p).toEqual({ q: 'magic', city: 'Pune', area: 'Wakad', artistType: 'dj', eventType: 'wedding', language: 'Hindi',
      readyToTravel: true, minPrice: 5000, maxPrice: 40000, minRating: 4.5, verifiedOnly: true, featuredOnly: true, sort: 'rating', page: 3 });
  });

  it('drops unknown enum values and junk numbers instead of sending them to the API', () => {
    expect(parseSearch(new URLSearchParams('artistType=juggler&eventType=party&sort=cheapest&page=-2&minRating=abc'))).toEqual({ city: 'Mumbai', sort: 'relevance', page: 1 });
  });
});

describe('toSearchString', () => {
  it('omits defaults and empty values so URLs stay short', () => {
    expect(toSearchString({ city: 'Mumbai', sort: 'relevance', page: 1, q: '', maxPrice: MAX_PRICE, verifiedOnly: false })).toBe('');
  });

  it('round-trips through parseSearch', () => {
    const params = { q: 'dj', city: 'Delhi', artistType: 'dj' as const, minRating: 4, featuredOnly: true, sort: 'price_low' as const, page: 2 };
    expect(parseSearch(new URLSearchParams(toSearchString(params)))).toEqual(params);
  });
});

describe('activeFilterCount', () => {
  it('counts sidebar filters but not q, city, sort or page', () => {
    expect(activeFilterCount({ q: 'x', city: 'Pune', sort: 'rating', page: 2 })).toBe(0);
    expect(activeFilterCount({ city: 'Pune', area: 'Wakad', verifiedOnly: true, maxPrice: 20000 })).toBe(3);
  });
});

import { mergeSearch } from './searchUrl';

describe('mergeSearch (review fix: debounced typing must not drop newer filters)', () => {
  it('applies changes on top of the latest URL and resets to page 1', () => {
    const latest = new URLSearchParams('artistType=magician&page=3');
    expect(mergeSearch(latest, { q: 'dj' })).toBe('q=dj&artistType=magician');
  });
  it('removes a key when its change is undefined', () => {
    expect(mergeSearch(new URLSearchParams('q=dj&city=Pune'), { q: undefined })).toBe('city=Pune');
  });
});
