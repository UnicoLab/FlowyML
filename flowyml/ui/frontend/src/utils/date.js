import { format, isValid } from 'date-fns';

export function formatDate(dateString, formatStr = 'MMM d, yyyy') {
    if (!dateString) return '-';

    const date = new Date(dateString);
    if (!isValid(date)) return '-';

    return format(date, formatStr);
}
