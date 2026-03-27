import { useState } from 'react'

/**
 * TableEditor — Editable KSERC data table.
 * 
 * Props:
 *   table: { number, caption, unit, columns, rows }
 *   onRowChange: (tableIdx, rowIdx, field, value) => void
 *   tableIdx: index of this table within the section
 *   readOnly: boolean
 */
export default function TableEditor({ table, onRowChange, tableIdx, readOnly = false }) {
    if (!table || !table.rows) return null

    const cols = table.columns || []

    return (
        <div style={{ margin: '16px 0', pageBreakInside: 'avoid' }}>
            {/* Caption */}
            {table.caption && (
                <p style={{
                    fontWeight: 700, textAlign: 'center', margin: '8px 0 4px',
                    fontFamily: 'var(--font-display)', fontSize: '0.85rem',
                    color: 'var(--text)',
                }}>
                    Table {table.number}: {table.caption}
                </p>
            )}
            {table.unit && (
                <p style={{
                    textAlign: 'right', fontSize: '0.7rem', fontStyle: 'italic',
                    color: 'var(--text-tertiary)', margin: '0 0 4px',
                }}>
                    {table.unit}
                </p>
            )}

            <div style={{ overflowX: 'auto' }}>
                <table className="data-table" style={{ fontSize: '0.8rem' }}>
                    <thead>
                        <tr>
                            {cols.map((col, i) => (
                                <th key={i} style={i > 1 ? { textAlign: 'right' } : {}}>{col}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {table.rows.map((row, ri) => {
                            const isTotal = row.is_total || false
                            const isHeader = row.is_header || false
                            const isGap = row.is_gap || false

                            return (
                                <tr key={ri} style={{
                                    fontWeight: isTotal || isGap ? 700 : 'normal',
                                    background: isHeader
                                        ? 'rgba(191,255,0,0.06)'
                                        : isTotal
                                            ? 'rgba(191,255,0,0.03)'
                                            : isGap
                                                ? 'rgba(255,200,0,0.06)'
                                                : 'transparent',
                                }}>
                                    {/* Sl. No. */}
                                    {(cols.includes('Sl. No.') || cols.includes('Sl.No.')) && (
                                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', width: 40 }}>
                                            {row.sl ?? ''}
                                        </td>
                                    )}

                                    {/* Particulars */}
                                    {(cols.includes('Particulars') || cols.includes('particular')) && (
                                        <td style={{ fontWeight: isTotal || isHeader ? 700 : 'normal' }}>
                                            {readOnly ? (
                                                row.particular || ''
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={row.particular || ''}
                                                    onChange={e => onRowChange(tableIdx, ri, 'particular', e.target.value)}
                                                    className="input-field"
                                                    style={{ width: '100%', fontSize: '0.78rem', padding: '3px 6px', background: 'transparent', border: 'none', borderBottom: '1px solid var(--border)' }}
                                                />
                                            )}
                                        </td>
                                    )}

                                    {/* Claimed column */}
                                    {row.claimed !== undefined && (
                                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                                            {row.claimed === '' ? '' : (
                                                readOnly ? (
                                                    typeof row.claimed === 'number' ? row.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : row.claimed
                                                ) : (
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        value={row.claimed}
                                                        onChange={e => onRowChange(tableIdx, ri, 'claimed', parseFloat(e.target.value) || 0)}
                                                        className="input-field"
                                                        style={{ width: 90, textAlign: 'right', fontSize: '0.78rem', padding: '3px 6px', fontFamily: 'var(--font-mono)' }}
                                                    />
                                                )
                                            )}
                                        </td>
                                    )}

                                    {/* Approved column */}
                                    {row.approved !== undefined && (
                                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--green)' }}>
                                            {row.approved === '' ? '' : (
                                                readOnly ? (
                                                    typeof row.approved === 'number' ? row.approved.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : row.approved
                                                ) : (
                                                    <input
                                                        type="number"
                                                        step="any"
                                                        value={row.approved}
                                                        onChange={e => onRowChange(tableIdx, ri, 'approved', parseFloat(e.target.value) || 0)}
                                                        className="input-field"
                                                        style={{ width: 90, textAlign: 'right', fontSize: '0.78rem', padding: '3px 6px', fontFamily: 'var(--font-mono)', color: 'var(--green)' }}
                                                    />
                                                )
                                            )}
                                        </td>
                                    )}

                                    {/* Amount column (for 2-col tables) */}
                                    {row.amount !== undefined && row.claimed === undefined && (
                                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                                            {readOnly ? (
                                                typeof row.amount === 'number' ? row.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : row.amount
                                            ) : (
                                                <input
                                                    type="number"
                                                    step="any"
                                                    value={row.amount}
                                                    onChange={e => onRowChange(tableIdx, ri, 'amount', parseFloat(e.target.value) || 0)}
                                                    className="input-field"
                                                    style={{ width: 90, textAlign: 'right', fontSize: '0.78rem', padding: '3px 6px', fontFamily: 'var(--font-mono)' }}
                                                />
                                            )}
                                        </td>
                                    )}
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
