import { useState } from 'react'
import { Chevron } from './ui'

/**
 * CourtHearingEditor — hearing date, licensee submissions, respondent position and
 * Commission observations that flow into the generated KSERC order.
 */
export default function CourtHearingEditor({ analysisId, existingData, onSaved }) {
    const [expanded, setExpanded] = useState(false)
    const [saving, setSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState(null)

    const [hearingDate, setHearingDate] = useState(existingData?.hearing_date || '')
    const [submissions, setSubmissions] = useState(existingData?.licensee_submissions?.length ? existingData.licensee_submissions : [''])
    const [respondentPosition, setRespondentPosition] = useState(existingData?.respondent_position || '')
    const [commissionObservations, setCommissionObservations] = useState(existingData?.commission_observations || '')

    const updateSubmission = (idx, text) => setSubmissions(prev => prev.map((s, i) => i === idx ? text : s))

    const handleSave = async () => {
        setSaving(true); setSaved(false); setError(null)
        try {
            const body = {
                analysis_id: analysisId,
                hearing_date: hearingDate,
                licensee_submissions: submissions.filter(s => s.trim()),
                respondent_position: respondentPosition,
                commission_observations: commissionObservations,
            }
            const resp = await fetch('/api/hearing-data', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
            })
            if (!resp.ok) throw new Error('Could not save hearing details')
            setSaved(true)
            onSaved?.(body)
            setTimeout(() => setSaved(false), 3000)
        } catch (err) {
            setError(err.message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="card">
            <button className="disclosure" onClick={() => setExpanded(e => !e)} aria-expanded={expanded}>
                <Chevron open={expanded} />
                <span style={{ flex: 1 }}>
                    <span className="h3" style={{ display: 'block' }}>Court hearing</span>
                    <span className="faint" style={{ fontSize: 12 }}>Hearing date, submissions and observations carried into the order</span>
                </span>
                {saved && <span className="pill pill-ok">Saved</span>}
                {hearingDate && !saved && <span className="pill pill-plain num">{hearingDate}</span>}
            </button>

            <div className={`collapse ${expanded ? 'is-open' : ''}`}>
                <div>
                    <div className="stack" style={{ padding: '6px 16px 18px 40px', gap: 18 }}>
                        <label className="field" style={{ maxWidth: 220 }}>
                            <span className="label">Hearing date</span>
                            <input type="date" className="input num" value={hearingDate} onChange={e => setHearingDate(e.target.value)} />
                        </label>

                        <div className="field">
                            <div className="row">
                                <span className="label">Licensee submissions</span>
                                <span className="spacer" />
                                <button className="btn btn-sm" onClick={() => setSubmissions(p => [...p, ''])}>Add point</button>
                            </div>
                            {submissions.map((sub, i) => (
                                <div key={i} className="row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                                    <span className="idx" style={{ paddingTop: 9, minWidth: 20 }}>{i + 1}.</span>
                                    <textarea className="textarea" rows={2} value={sub} onChange={e => updateSubmission(i, e.target.value)}
                                        placeholder="What the licensee submitted during the hearing" />
                                    {submissions.length > 1 && (
                                        <button className="btn btn-ghost btn-sm btn-danger" style={{ marginTop: 5 }}
                                            onClick={() => setSubmissions(p => p.filter((_, j) => j !== i))} aria-label="Remove point">Remove</button>
                                    )}
                                </div>
                            ))}
                        </div>

                        <label className="field">
                            <span className="label">Respondent's (KSEB) position</span>
                            <textarea className="textarea" rows={3} value={respondentPosition} onChange={e => setRespondentPosition(e.target.value)}
                                placeholder="KSEB Ltd's submissions and verification" />
                        </label>

                        <label className="field">
                            <span className="label">Commission's observations</span>
                            <textarea className="textarea" rows={3} value={commissionObservations} onChange={e => setCommissionObservations(e.target.value)}
                                placeholder="The Commission's observations and findings" />
                        </label>

                        <div className="row">
                            {error && <span className="bad" style={{ fontSize: 12 }}>{error}</span>}
                            {saved && <span className="ok" style={{ fontSize: 12 }}>Saved — included in the next generated order</span>}
                            <span className="spacer" />
                            <button className="btn btn-accent" disabled={saving} onClick={handleSave}>{saving ? 'Saving…' : 'Save hearing details'}</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
