import { useState } from 'react'
import TableEditor from './TableEditor'

/**
 * SectionEditor — Editable section with paragraphs, tables, and decision.
 * 
 * Props:
 *   section: { id, title, paragraphs, tables, decision }
 *   sectionIdx: index in sections array
 *   onParagraphChange: (sectionIdx, paraIdx, text) => void
 *   onTableRowChange: (sectionIdx, tableIdx, rowIdx, field, value) => void
 *   onDecisionChange: (sectionIdx, text) => void
 *   editMode: boolean
 */
export default function SectionEditor({
    section, sectionIdx,
    onParagraphChange, onTableRowChange, onDecisionChange,
    editMode = false,
}) {
    const [expanded, setExpanded] = useState(false)

    if (!section) return null

    const statusColor = section.decision
        ? 'var(--green)'
        : 'var(--text-tertiary)'

    return (
        <div className="card animate-slide-up" style={{
            animationDelay: `${sectionIdx * 30}ms`,
            borderLeftWidth: 2,
            borderLeftColor: statusColor,
        }}>
            {/* Section header — clickable to expand */}
            <button
                onClick={() => setExpanded(!expanded)}
                style={{
                    width: '100%', padding: '14px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className="mono" style={{
                        color: 'var(--text-tertiary)', fontSize: '10px', width: 24,
                    }}>
                        {String(sectionIdx + 1).padStart(2, '0')}
                    </span>
                    <div>
                        <h4 style={{
                            fontFamily: 'var(--font-display)', fontWeight: 700,
                            fontSize: '0.88rem', letterSpacing: '-0.02em',
                            color: 'var(--text)', lineHeight: 1.3,
                        }}>
                            {section.title}
                        </h4>
                        <span className="mono" style={{
                            fontSize: '0.65rem', color: 'var(--text-tertiary)', marginTop: 2,
                        }}>
                            {section.paragraphs?.length || 0} paragraphs · {section.tables?.length || 0} tables
                        </span>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {section.decision && (
                        <span className="badge-compliant" style={{ fontSize: '8px' }}>
                            HAS DECISION
                        </span>
                    )}
                    <span style={{
                        color: 'var(--text-tertiary)', fontSize: '12px',
                        transition: 'transform 0.2s',
                        transform: expanded ? 'rotate(180deg)' : 'none',
                    }}>▾</span>
                </div>
            </button>

            {/* Expanded content */}
            {expanded && (
                <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>
                    {/* Paragraphs */}
                    <div style={{ marginTop: 12 }}>
                        {section.paragraphs?.map((para, pi) => (
                            <div key={pi} style={{
                                display: 'flex', gap: 8, marginBottom: 10,
                                alignItems: 'flex-start',
                            }}>
                                <span className="mono" style={{
                                    color: 'var(--accent)', fontSize: '0.75rem',
                                    fontWeight: 700, minWidth: 28, paddingTop: 6,
                                }}>
                                    {para.seq}.
                                </span>
                                {editMode ? (
                                    <textarea
                                        value={para.text}
                                        onChange={e => onParagraphChange(sectionIdx, pi, e.target.value)}
                                        rows={Math.max(3, Math.ceil(para.text.length / 80))}
                                        className="input-field"
                                        style={{
                                            flex: 1, resize: 'vertical',
                                            fontFamily: 'var(--font-body)',
                                            fontSize: '0.82rem', lineHeight: 1.7,
                                            padding: '8px 12px',
                                            ...(para.is_decision ? { fontWeight: 700, borderColor: 'var(--green)' } : {}),
                                        }}
                                    />
                                ) : (
                                    <p style={{
                                        flex: 1, fontSize: '0.82rem', lineHeight: 1.7,
                                        color: 'rgba(255,255,255,0.7)', margin: 0,
                                        ...(para.is_decision ? { fontWeight: 700, color: 'var(--green)' } : {}),
                                    }}>
                                        {para.text}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Tables */}
                    {section.tables?.map((table, ti) => (
                        <TableEditor
                            key={ti}
                            table={table}
                            tableIdx={ti}
                            readOnly={!editMode}
                            onRowChange={(tableIdx, rowIdx, field, value) =>
                                onTableRowChange(sectionIdx, tableIdx, rowIdx, field, value)
                            }
                        />
                    ))}
                </div>
            )}
        </div>
    )
}
