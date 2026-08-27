import { describe, expect, it } from 'vitest';
import { formatDate } from '../date';

/**
 * date-fns throws `RangeError: Invalid time value` when asked to format an
 * invalid date, so calling `format(new Date(x), ...)` directly on API data
 * takes down the whole page as soon as one record has a bad timestamp. That
 * happened in production: a single run row with `start_time: "unknown"`
 * replaced the Dashboard with the error boundary.
 */
describe('formatDate', () => {
    it('formats a valid ISO timestamp', () => {
        expect(formatDate('2026-03-14T09:26:53Z', 'yyyy-MM-dd')).toBe('2026-03-14');
    });

    it('uses a sensible default format', () => {
        expect(formatDate('2026-03-14T09:26:53Z')).toBe('Mar 14, 2026');
    });

    it.each([
        ['undefined', undefined],
        ['null', null],
        ['empty string', ''],
        ['a non-date word', 'unknown'],
        ['a malformed date', 'not-a-date'],
        ['NaN', NaN],
    ])('returns a placeholder rather than throwing for %s', (_label, value) => {
        expect(() => formatDate(value)).not.toThrow();
        expect(formatDate(value)).toBe('-');
    });

    it('never renders the Unix epoch for a missing value', () => {
        // `new Date(null)` is 1970-01-01, so an unset timestamp would
        // otherwise be displayed as a real date.
        expect(formatDate(null)).not.toContain('1970');
        expect(formatDate(undefined)).not.toContain('1970');
    });

    it('accepts a Date instance', () => {
        expect(formatDate(new Date('2026-03-14T00:00:00Z'), 'yyyy')).toBe('2026');
    });

    it('rejects an invalid Date instance', () => {
        expect(formatDate(new Date('nonsense'))).toBe('-');
    });
});
