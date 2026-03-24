import { useState } from 'react'

/**
 * CourtHearingEditor — allows the user to input court hearing details
 * (hearing date, licensee submissions, respondent position, commission observations)
 * that flow through to the generated KSERC order PDF.
 */
export default function CourtHearingEditor({ analysisId, existingData, onSaved }) {
    const [expanded, setExpanded] = useState(false)
    const [saving, setSaving] = useState(false)
    const [saved, setSaved] = useState(false)

    const [hearingDate, setHearingDate] = useState(existingData?.hearing_date || '')
    const [submissions, setSubmissions] = useState(existingData?.licensee_submissions || [''])
    const [respondentPosition, setRespondentPosition] = useState(existingData?.respondent_position || '')
    const [commissionObservations, setCommissionObservations] = useState(existingData?.commission_observations || '')

    const addSubmission = () => setSubmissions(prev => [...prev, ''])
    const removeSubmission = (idx) => setSubmissions(prev => prev.filter((_, i) => i !== idx))
    const updateSubmission = (idx, text) => setSubmissions(prev => prev.map((s, i) => i === idx ? text : s))

    const handleSave = async () => {
        setSaving(true)
        setSaved(false)
        try {
            const body = {
                analysis_id: analysisId,
                hearing_date: hearingDate,
                licensee_submissions: submissions.filter(s => s.trim()),
                respondent_position: respondentPosition,
                commission_observations: commissionObservations,
            }
            const resp = await fetch('/api/hearing-data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            })
            if (!resp.ok) throw new Error('Failed to save hearing data')
            setSaved(true)
            if (onSaved) onSaved(body)
            setTimeout(() => setSaved(false), 3000)
        } catch (err) {
            console.error('Save hearing data failed:', err)
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="glass-card animate-slide-up" style={{ overflow: 'hidden', borderColor: 'rgba(100, 180, 255, 0.25)' }}>
            {/* Header — always visible */}
            <button
                onClick={() => setExpanded(e => !e)}
                style={{
                    width: '100%', padding: '16px 22px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'linear-gradient(135deg, rgba(100,180,255,0.06), rgba(60,120,255,0.03))',
                    border: 'none', borderBottom: expanded ? '1px solid var(--border)' : 'none',
                    cursor: 'pointer', textAlign: 'left',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: '1.2rem' }}>⚖️</span>
                    <div>
                        <span className="mono-wide" style={{ color: '#64b4ff', fontSize: '10px' }}>
                            COURT HEARING DETAILS
                        </span>
                        <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                            Add hearing date, submissions, and observations for the order PDF
                        </p>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {saved && <span className="neon-tag tag-approved" style={{ fontSize: '9px' }}>✓ SAVED</span>}
                    <span style={{
                        color: 'var(--text-tertiary)', fontSize: '14px',
                        transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'none',
                    }}>▾</span>
                </div>
            </button>

            {/* Expanded content */}
            {expanded && (
                <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 20 }}>

                    {/* Hearing Date */}
                    <div>
                        <label className="mono-wide" style={{ fontSize: '9px', display: 'block', marginBottom: 8, color: 'var(--text-secondary)' }}>
                            📅 HEARING DATE
                        </label>
                        <input
                            type="date"
                            value={hearingDate}
                            onChange={e => setHearingDate(e.target.value)}
                            className="neon-input"
                            style={{ width: 220, fontFamily: 'var(--font-mono)', fontSize: '0.85rem', padding: '8px 12px' }}
                        />
                    </div>

                    {/* Licensee Submissions */}
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                            <label className="mono-wide" style={{ fontSize: '9px', color: 'var(--text-secondary)' }}>
                                📝 LICENSEE SUBMISSIONS
                            </label>
                            <button
                                onClick={addSubmission}
                                className="ghost-btn"
                                style={{ fontSize: '0.65rem', padding: '4px 12px' }}
                            >
                                + Add Point
                            </button>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {submissions.map((sub, i) => (
                                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                                    <span className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '10px', paddingTop: 10, minWidth: 20 }}>
                                        {i + 1}.
                                    </span>
                                    <textarea
                                        value={sub}
                                        onChange={e => updateSubmission(i, e.target.value)}
                                        rows={2}
                                        className="neon-input"
                                        placeholder="Enter what the licensee submitted during the hearing..."
                                        style={{
                                            flex: 1, resize: 'vertical',
                                            fontFamily: 'var(--font-body)', fontSize: '0.8rem',
                                            lineHeight: 1.6, padding: '8px 12px',
                                        }}
                                    />
                                    {submissions.length > 1 && (
                                        <button
                                            onClick={() => removeSubmission(i)}
                                            style={{
                                                background: 'none', border: 'none', cursor: 'pointer',
                                                color: 'var(--red)', fontSize: '14px', paddingTop: 6,
                                            }}
                                            title="Remove"
                                        >
                                            ×
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Respondent's Position */}
                    <div>
                        <label className="mono-wide" style={{ fontSize: '9px', display: 'block', marginBottom: 8, color: 'var(--text-secondary)' }}>
                            🏛️ RESPONDENT'S (KSEB) POSITION
                        </label>
                        <textarea
                            value={respondentPosition}
                            onChange={e => setRespondentPosition(e.target.value)}
                            rows={3}
                            className="neon-input"
                            placeholder="Enter the respondent's (KSEB Ltd) submissions and verification..."
                            style={{
                                width: '100%', resize: 'vertical',
                                fontFamily: 'var(--font-body)', fontSize: '0.8rem',
                                lineHeight: 1.6, padding: '8px 12px',
                            }}
                        />
                    </div>

                    {/* Commission's Observations */}
                    <div>
                        <label className="mono-wide" style={{ fontSize: '9px', display: 'block', marginBottom: 8, color: 'var(--text-secondary)' }}>
                            📋 COMMISSION'S OBSERVATIONS
                        </label>
                        <textarea
                            value={commissionObservations}
                            onChange={e => setCommissionObservations(e.target.value)}
                            rows={3}
                            className="neon-input"
                            placeholder="Enter the Commission's observations and findings..."
                            style={{
                                width: '100%', resize: 'vertical',
                                fontFamily: 'var(--font-body)', fontSize: '0.8rem',
                                lineHeight: 1.6, padding: '8px 12px',
                            }}
                        />
                    </div>

                    {/* Save Button */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 4 }}>
                        {saved && (
                            <span className="mono" style={{ color: 'var(--green)', fontSize: '0.75rem', alignSelf: 'center' }}>
                                ✓ Hearing details saved — will appear in the generated order
                            </span>
                        )}
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="laser-btn"
                            style={{ fontSize: '0.7rem', padding: '8px 22px', opacity: saving ? 0.5 : 1 }}
                        >
                            {saving ? '⏳ Saving…' : '💾 Save Hearing Details'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
