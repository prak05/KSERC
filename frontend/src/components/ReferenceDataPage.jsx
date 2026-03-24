import React, { useState, useEffect, useRef } from 'react'
import NeonSelect from './NeonSelect'

const TABS = [
    { id: 'economic', label: '💹 Economic', icon: '01' },
    { id: 'myt', label: '⚖️ MYT Norms', icon: '02' },
    { id: 'interim', label: '📜 Interim Orders', icon: '03' },
    { id: 'past', label: '🗂️ Past Orders', icon: '04' },
]

const LICENSEES = ['Technopark', 'Infopark', 'CSEZA', 'KDHP']
const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

// ─── Extraction Review ───────────────────────────────────────────────
function ExtractionReviewTable({ rows, onRowChange }) {
    if (!rows || rows.length === 0) return (
        <p className="mono" style={{ textAlign: 'center', padding: 24, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', color: 'var(--text-tertiary)' }}>
            No data extracted.
        </p>
    )
    return (
        <div style={{ overflowX: 'auto', marginTop: 12 }}>
            <table className="neon-table">
                <thead>
                    <tr>
                        <th style={{ textAlign: 'center', width: 50 }}>Sl.</th>
                        <th>Licensee</th>
                        <th>Year</th>
                        <th>Field</th>
                        <th style={{ textAlign: 'right' }}>Value</th>
                        <th>Unit</th>
                        <th style={{ textAlign: 'center' }}>Page</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, idx) => (
                        <tr key={idx}>
                            <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{String(idx + 1).padStart(2, '0')}</td>
                            <td style={{ fontWeight: 500 }}>{row.licensee}</td>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>{row.year}</td>
                            <td>{row.field}</td>
                            <td style={{ textAlign: 'right' }}>
                                <input type="number" step="any" value={row.value ?? ''}
                                    onChange={e => onRowChange(idx, 'value', parseFloat(e.target.value) || 0)}
                                    className="neon-input" style={{ width: 90, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '11px', padding: '4px 8px' }} />
                            </td>
                            <td className="mono">{row.unit}</td>
                            <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{row.page ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─── PDF Upload Section ──────────────────────────────────────────────
function PDFUploadSection({ orderType, label, description }) {
    const [file, setFile] = useState(null)
    const [orderNumber, setOrderNumber] = useState('')
    const [licensee, setLicensee] = useState('')
    const [financialYear, setFinancialYear] = useState('')
    const [loading, setLoading] = useState(false)
    const [extracted, setExtracted] = useState(null)
    const [editableRows, setEditableRows] = useState([])
    const [saveStatus, setSaveStatus] = useState(null)
    const [error, setError] = useState(null)
    const [orders, setOrders] = useState([])
    const fileRef = useRef()

    useEffect(() => { fetchOrders() }, [saveStatus])
    const fetchOrders = async () => {
        try { const res = await fetch(`/api/reference/orders?order_type=${orderType}`); const d = await res.json(); setOrders(d.orders || []) } catch { }
    }

    const handleUpload = async () => {
        if (!file) return
        setLoading(true); setError(null); setSaveStatus(null)
        const form = new FormData()
        form.append('file', file); form.append('order_type', orderType)
        form.append('order_number', orderNumber); form.append('licensee', licensee); form.append('financial_year', financialYear)
        try {
            const res = await fetch('/api/reference/orders/extract', { method: 'POST', body: form })
            if (!res.ok) throw new Error('Extraction failed')
            const data = await res.json(); setExtracted(data); setEditableRows(data.extracted_rows || [])
        } catch (e) { setError(e.message) } finally { setLoading(false) }
    }

    const handleRowChange = (idx, field, value) => { const u = [...editableRows]; u[idx] = { ...u[idx], [field]: value }; setEditableRows(u) }

    const handleConfirm = async () => {
        if (!extracted) return; setSaveStatus('saving')
        try {
            const res = await fetch('/api/reference/orders/confirm', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: extracted.order_id, order_type: orderType, order_number: extracted.order_number || orderNumber, control_period: extracted.control_period || '', document_type: extracted.document_type || orderType, confirmed_rows: editableRows }),
            })
            const d = await res.json(); setSaveStatus(d.message || 'Saved!')
            setExtracted(null); setEditableRows([]); setFile(null)
            if (fileRef.current) fileRef.current.value = ''
        } catch (e) { setSaveStatus('Error: ' + e.message) }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="glass-card" style={{ padding: '24px 28px' }}>
                <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1rem', letterSpacing: '-0.03em', textTransform: 'none', lineHeight: 1.3, marginBottom: 4 }}>{label}</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16, maxWidth: 700 }}>{description}</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginBottom: 14 }}>
                    <input ref={fileRef} type="file" accept=".pdf" onChange={e => setFile(e.target.files[0])}
                        style={{ display: 'none' }} />
                    <div
                        onClick={() => fileRef.current?.click()}
                        style={{
                            gridColumn: 'span 2', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
                            padding: '12px 16px', background: 'rgba(255,255,255,0.03)', border: '1px dashed',
                            borderColor: file ? 'var(--border-accent)' : 'var(--border)', borderRadius: 'var(--radius-sm)',
                            transition: 'all 0.3s var(--ease-expo)',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-accent)'; e.currentTarget.style.background = 'rgba(191,255,0,0.03)' }}
                        onMouseLeave={e => { if (!file) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)' } }}
                    >
                        <span style={{ fontSize: '1.2rem', opacity: file ? 1 : 0.4 }}>{file ? '📄' : '📎'}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <p className="mono" style={{ fontSize: '11px', fontWeight: 600, color: file ? 'var(--accent)' : 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {file ? file.name : 'Click to select PDF…'}
                            </p>
                            {file && <p className="mono" style={{ fontSize: '9px', color: 'var(--text-tertiary)', marginTop: 2 }}>{(file.size / 1024).toFixed(0)} KB</p>}
                        </div>
                        {file && <span onClick={e => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = '' }} style={{ fontSize: '10px', color: 'var(--text-tertiary)', cursor: 'pointer', padding: '4px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', transition: 'all 0.2s' }}
                            onMouseEnter={e => { e.currentTarget.style.color = 'var(--red)'; e.currentTarget.style.borderColor = 'var(--red)' }}
                            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-tertiary)'; e.currentTarget.style.borderColor = 'var(--border)' }}
                        >✕</span>}
                    </div>
                    <input type="text" placeholder="Order No." value={orderNumber} onChange={e => setOrderNumber(e.target.value)}
                        className="neon-input" style={{ fontSize: '11px' }} />
                    {orderType === 'past_order' && (
                        <NeonSelect value={licensee} onChange={setLicensee} options={LICENSEES} placeholder="Licensee" />
                    )}
                    {orderType === 'past_order' && (
                        <NeonSelect value={financialYear} onChange={setFinancialYear} options={FINANCIAL_YEARS} placeholder="Year" />
                    )}
                </div>
                <button onClick={handleUpload} disabled={!file || loading} className="laser-btn" style={{ fontSize: '0.7rem', padding: '10px 22px', opacity: (!file || loading) ? 0.3 : 1 }}>
                    {loading ? '⏳ Extracting…' : '🔼 Upload & Extract'}
                </button>
                {error && <p className="mono" style={{ color: 'var(--red)', marginTop: 8 }}>🔴 {error}</p>}
            </div>

            {extracted && editableRows.length > 0 && (
                <div className="glass-card animate-slide-up" style={{ borderColor: 'rgba(0,255,136,0.3)', padding: '24px 28px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 12, borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
                        <span className="mono" style={{ color: 'var(--green)' }}>✅ Extracted {editableRows.length} values</span>
                        <span className="neon-tag tag-neutral">Edit before confirming</span>
                    </div>
                    <ExtractionReviewTable rows={editableRows} onRowChange={handleRowChange} />
                    <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                        <button onClick={handleConfirm} className="laser-btn" style={{ fontSize: '0.7rem', padding: '10px 22px' }}>💾 Confirm & Save</button>
                        <button onClick={() => { setExtracted(null); setEditableRows([]) }} className="ghost-btn">Cancel</button>
                    </div>
                </div>
            )}

            {saveStatus && (
                <div className="glass-card" style={{ borderColor: 'rgba(0,255,136,0.3)', padding: '10px 18px' }}>
                    <p className="mono" style={{ color: 'var(--green)' }}>🟢 {saveStatus}</p>
                </div>
            )}

            {orders.length > 0 && (
                <div className="glass-card" style={{ padding: '20px 24px' }}>
                    <p className="mono-wide" style={{ color: 'var(--accent)', marginBottom: 12, fontSize: '9px' }}>📂 Uploaded Orders</p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                        {orders.map(o => (
                            <div key={o.id} className="lum-card" style={{ padding: '14px 16px' }}>
                                <span style={{ fontWeight: 600, fontSize: '0.8rem', display: 'block', marginBottom: 4 }}>{o.order_number || 'Unnamed'}</span>
                                <span className="mono" style={{ color: 'var(--text-tertiary)' }}>
                                    {o.licensee} {o.financial_year && `• ${o.financial_year}`}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

// ─── Economic Indicators ─────────────────────────────────────────────
function EconomicIndicatorsSection() {
    const [indicators, setIndicators] = useState([])
    const [editing, setEditing] = useState({})
    const [saveStatus, setSaveStatus] = useState({})
    const [newRow, setNewRow] = useState({ financial_year: '', wpi_pct: '', cpi_pct: '', sbi_plr_pct: '', hsd_price_rs: '', power_purchase_rate_rs_per_kwh: '' })

    useEffect(() => {
        fetch('/api/reference/economic-indicators').then(r => r.json()).then(d => setIndicators(d.indicators || [])).catch(() => {})
    }, [saveStatus])

    const handleSave = async (row) => {
        try {
            await fetch('/api/reference/economic-indicators', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(row) })
            setSaveStatus(s => ({ ...s, [row.financial_year]: '✓' }))
            setTimeout(() => setSaveStatus(s => { const n = { ...s }; delete n[row.financial_year]; return n }), 2000)
        } catch { setSaveStatus(s => ({ ...s, [row.financial_year]: '✗' })) }
    }

    const handleAddNew = async () => {
        if (!newRow.financial_year) return
        await handleSave({ financial_year: newRow.financial_year, wpi_pct: parseFloat(newRow.wpi_pct) || null, cpi_pct: parseFloat(newRow.cpi_pct) || null, sbi_plr_pct: parseFloat(newRow.sbi_plr_pct) || null, hsd_price_rs: parseFloat(newRow.hsd_price_rs) || null, power_purchase_rate_rs_per_kwh: parseFloat(newRow.power_purchase_rate_rs_per_kwh) || null })
        setNewRow({ financial_year: '', wpi_pct: '', cpi_pct: '', sbi_plr_pct: '', hsd_price_rs: '', power_purchase_rate_rs_per_kwh: '' })
    }

    const cols = [
        { key: 'wpi_pct', label: 'WPI %' }, { key: 'cpi_pct', label: 'CPI %' }, { key: 'sbi_plr_pct', label: 'SBI PLR %' },
        { key: 'hsd_price_rs', label: 'HSD ₹/L' }, { key: 'power_purchase_rate_rs_per_kwh', label: 'PPC ₹/kWh' },
    ]

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: 600 }}>Economic indicators per FY. Used by auditor for O&M escalation.</p>
            <div style={{ overflowX: 'auto' }}>
                <table className="neon-table">
                    <thead>
                        <tr>
                            <th>Year</th>
                            {cols.map(c => <th key={c.key} style={{ textAlign: 'right' }}>{c.label}</th>)}
                            <th style={{ textAlign: 'center' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {indicators.map(row => {
                            const isE = editing[row.financial_year]; const eR = isE || row
                            return (
                                <tr key={row.financial_year}>
                                    <td style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.9rem' }}>{row.financial_year}</td>
                                    {cols.map(c => (
                                        <td key={c.key} style={{ textAlign: 'right' }}>
                                            {isE ? <input type="number" step="any" value={eR[c.key] ?? ''} onChange={e => setEditing(ed => ({ ...ed, [row.financial_year]: { ...eR, [c.key]: e.target.value } }))} className="neon-input" style={{ width: 75, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '11px', padding: '3px 6px' }} />
                                                : <span style={{ fontFamily: 'var(--font-mono)' }}>{row[c.key] ?? <span style={{ color: 'var(--text-tertiary)' }}>—</span>}</span>}
                                        </td>
                                    ))}
                                    <td style={{ textAlign: 'center' }}>
                                        {isE ? (
                                            <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                                                <button onClick={() => { handleSave({ financial_year: row.financial_year, ...eR }); setEditing(e => { const n = { ...e }; delete n[row.financial_year]; return n }) }} className="laser-btn" style={{ fontSize: '9px', padding: '4px 12px' }}>Save</button>
                                                <button onClick={() => setEditing(e => { const n = { ...e }; delete n[row.financial_year]; return n })} className="ghost-btn" style={{ fontSize: '9px', padding: '4px 12px' }}>Cancel</button>
                                            </div>
                                        ) : (
                                            <div style={{ display: 'flex', gap: 6, justifyContent: 'center', alignItems: 'center' }}>
                                                <button onClick={() => setEditing(e => ({ ...e, [row.financial_year]: { ...row } }))} className="ghost-btn" style={{ fontSize: '9px', padding: '4px 12px' }}>Edit</button>
                                                {saveStatus[row.financial_year] && <span className="neon-tag tag-approved">{saveStatus[row.financial_year]}</span>}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            )
                        })}
                        <tr style={{ borderTop: '1px solid var(--border-accent)' }}>
                            <td>
                                <NeonSelect value={newRow.financial_year} onChange={v => setNewRow(r => ({ ...r, financial_year: v }))} options={FINANCIAL_YEARS.filter(y => !indicators.find(i => i.financial_year === y))} placeholder="+ Add" />
                            </td>
                            {cols.map(c => (
                                <td key={c.key} style={{ textAlign: 'right' }}>
                                    <input type="number" step="any" placeholder="0" value={newRow[c.key]} onChange={e => setNewRow(r => ({ ...r, [c.key]: e.target.value }))} className="neon-input" style={{ width: 75, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '11px', padding: '3px 6px' }} />
                                </td>
                            ))}
                            <td style={{ textAlign: 'center' }}>
                                <button onClick={handleAddNew} disabled={!newRow.financial_year} className="laser-btn" style={{ fontSize: '9px', padding: '5px 14px', opacity: newRow.financial_year ? 1 : 0.3 }}>Add</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// ─── MYT Norms ──────────────────────────────────────────────────────
function MYTNormsSection() {
    const [baselines, setBaselines] = useState({}); const [selectedLicensee, setSelectedLicensee] = useState('Infopark')
    const [selectedYear, setSelectedYear] = useState('2024-25'); const [editing, setEditing] = useState(false)
    const [editValues, setEditValues] = useState({}); const [saveStatus, setSaveStatus] = useState(null)

    useEffect(() => { fetch('/api/reference/myt-baselines').then(r => r.json()).then(d => setBaselines(d.baselines || {})).catch(() => {}) }, [saveStatus])

    const currentNorms = baselines[selectedLicensee]?.baselines?.[selectedYear] || {}
    const availableYears = selectedLicensee && baselines[selectedLicensee] ? Object.keys(baselines[selectedLicensee]?.baselines || {}) : FINANCIAL_YEARS

    const handleSave = async () => {
        const rows = Object.entries(editValues).map(([k, v]) => ({ field_key: k, licensee: selectedLicensee, year: selectedYear, value: parseFloat(v) || 0, field: k, unit: 'Rs Lakhs' }))
        try {
            const res = await fetch('/api/reference/orders/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: 'manual', order_type: 'myt_order', order_number: '', control_period: '', document_type: 'MANUAL_EDIT', confirmed_rows: rows }) })
            const d = await res.json(); setSaveStatus(d.message || 'Saved'); setEditing(false)
        } catch (e) { setSaveStatus('Error: ' + e.message) }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: 600 }}>MYT baselines per licensee. Overrides apply to subsequent audits.</p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                {LICENSEES.map(l => (
                    <button key={l} onClick={() => setSelectedLicensee(l)}
                        className={selectedLicensee === l ? 'laser-btn' : 'ghost-btn'}
                        style={{ fontSize: '0.65rem', padding: '8px 18px' }}>{l}</button>
                ))}
                <NeonSelect value={selectedYear} onChange={setSelectedYear} options={availableYears} placeholder="Select year" style={{ marginLeft: 'auto', minWidth: 140 }} />
            </div>

            {Object.keys(currentNorms).length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                    <table className="neon-table">
                        <thead><tr><th>Field</th><th style={{ textAlign: 'right' }}>Value</th><th>Unit</th></tr></thead>
                        <tbody>
                            {Object.entries(currentNorms).map(([key, val]) => {
                                const unit = key.includes('pct') || key.includes('loss') ? '%' : key.includes('rs_per_kwh') ? 'Rs/kWh' : 'Rs Lakhs'
                                return (
                                    <tr key={key}>
                                        <td style={{ fontWeight: 500, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</td>
                                        <td style={{ textAlign: 'right' }}>
                                            {editing ? <input type="number" step="any" defaultValue={val} onChange={e => setEditValues(v => ({ ...v, [key]: e.target.value }))} className="neon-input" style={{ width: 110, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', padding: '4px 8px' }} />
                                                : <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)', fontSize: '0.9rem' }}>{val}</span>}
                                        </td>
                                        <td className="mono" style={{ color: 'var(--text-tertiary)' }}>{unit}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div style={{ textAlign: 'center', padding: 40, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
                    <p className="mono" style={{ color: 'var(--text-tertiary)' }}>No norms for {selectedLicensee} ({selectedYear})</p>
                </div>
            )}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                {editing ? <>
                    <button onClick={handleSave} className="laser-btn" style={{ fontSize: '0.7rem', padding: '8px 20px' }}>💾 Save</button>
                    <button onClick={() => { setEditing(false); setEditValues({}) }} className="ghost-btn">Cancel</button>
                </> : <button onClick={() => { setEditing(true); setEditValues({}) }} className="ghost-btn ghost-btn-accent">🖊️ Edit</button>}
                {saveStatus && <span className="neon-tag tag-approved">{saveStatus}</span>}
            </div>
        </div>
    )
}

// ─── Main ───────────────────────────────────────────────────────────
export default function ReferenceDataPage() {
    const [activeTab, setActiveTab] = useState('economic')

    return (
        <div className="animate-slide-up" style={{ maxWidth: 1600, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div>
                <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', letterSpacing: '-0.05em', marginBottom: 8 }}>Reference Data</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: 600 }}>
                    Manage economic indicators, MYT norms, and reference orders. Changes affect all audit runs.
                </p>
            </div>

            <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)' }}>
                {TABS.map(tab => (
                    <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.2em', textTransform: 'uppercase',
                        padding: '14px 22px', border: 'none', cursor: 'pointer', background: 'transparent',
                        borderBottom: activeTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
                        color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-secondary)',
                        transition: 'all 0.3s var(--ease-expo)', display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                        <span style={{ opacity: 0.3, fontSize: '9px' }}>{tab.icon}</span>
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="glass-card" style={{ padding: '28px 32px', minHeight: 400 }}>
                <div className="animate-fade-in" key={activeTab}>
                    {activeTab === 'economic' && <EconomicIndicatorsSection />}
                    {activeTab === 'myt' && <MYTNormsSection />}
                    {activeTab === 'interim' && <PDFUploadSection orderType="interim_tariff" label="Upload MYT / Interim Order" description="Gemini extracts all ARR component norms across financial years." />}
                    {activeTab === 'past' && <PDFUploadSection orderType="past_order" label="Upload Finalized Truing-Up Order" description="Gemini extracts approved amounts for precedence and RAG." />}
                </div>
            </div>
        </div>
    )
}
