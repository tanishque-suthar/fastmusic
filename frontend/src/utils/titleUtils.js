/**
 * Cleans up a title by removing underscores, UIDs, and common suffixes
 * @param {string} title - The original title
 * @returns {string} - The cleaned title
 */
export function cleanTitle(title) {
    if (!title) return title;

    // Remove UID at the end (UUID4 first 8 chars: letters a-f, numbers 0-9, possibly hyphens)
    // Pattern: _XXXXXXXX where X is [a-f0-9-] (8 characters from UUID)
    let cleaned = title.replace(/_[a-f0-9-]{8}$/i, '');

    // Replace underscores with spaces
    cleaned = cleaned.replace(/_/g, ' ');

    // Replace multiple consecutive spaces with a single space
    cleaned = cleaned.replace(/\s+/g, ' ');

    // Remove common prefixes and suffixes (case insensitive)
    const termsToRemove = [
        'official music video',
        'official video',
        'music video',
        'official audio',
        'official lyric video',
        'lyric video',
        'lyrics video',
        'official',
        'hd',
        'hq',
        '4k',
        'live',
        'live performance',
        'acoustic version',
        'acoustic',
        'remix',
        'extended version',
        'radio edit',
        'clean version',
        'explicit version'
    ];

    // Remove terms from the beginning of the title (prefixes)
    termsToRemove.forEach(term => {
        // First match the term at the beginning, then check if followed by separators
        const prefixRegex = new RegExp(`^\\s*\\(?${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\)?\\s*(?:for|of|:|-|\\s)+`, 'gi');
        cleaned = cleaned.replace(prefixRegex, '');
    });

    // Remove terms from the end of the title (suffixes)
    termsToRemove.forEach(term => {
        const suffixRegex = new RegExp(`\\s*\\(?${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\)?\\s*$`, 'gi');
        cleaned = cleaned.replace(suffixRegex, '');
    });

    // Clean up any remaining parentheses or brackets at the end
    cleaned = cleaned.replace(/\s*[\(\[\{][\)\]\}]*\s*$/, '');

    // Replace multiple consecutive spaces with a single space again
    cleaned = cleaned.replace(/\s+/g, ' ');

    // Trim any extra spaces at the beginning and end
    cleaned = cleaned.trim();

    return cleaned;
}