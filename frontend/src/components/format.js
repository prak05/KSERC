/* Number formatting — Indian grouping, two decimals, tabular in the UI. */

export const fmt = (v, digits = 2) =>
    typeof v === 'number' && Number.isFinite(v)
        ? v.toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
        : '—'

export const signed = (v) => (typeof v === 'number' && v > 0 ? '+' : '') + fmt(v)
