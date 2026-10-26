import { useEffect, useRef, useState } from 'react'
import { Notice, PageHead } from './ui'

const TABS = [
    { id: 'economic', label: 'Economic indicators' },
    { id: 'myt', label: 'MYT norms' },
    { id: 'interim', label: 'Interim orders' },
    { id: 'past', label: 'Past orders' },
]

const LICENSEES = ['Technopark', 'Infopark', 'CSEZA', 'KDHP']
const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

function ExtractionReviewTable({ rows, onRowChange }) {
    if (!rows?.length) return <div className="empty">No data extracted.</div>
    return (
        <div className="table-wrap">
            <table className="table">
                <thead><tr><th style={{ width: 48 }}>#</th><th>Licensee</th><th>Year</th><th>Field</th><th className="r">Value</th><th>Unit</th><th className="r">Page</th></tr></thead>
                <tbody>
                    {rows.map((row, idx) => (
                        <tr key={idx}>
                            <td className="idx">{String(idx + 1).padStart(2, '0')}</td>
                            <td>{row.licensee}</td>
                            <td className="num">{row.year}</td>
                            <td>{row.field}</td>
                            <td className="r"><input type="number" step="any" className="input input-sm num" style={{ width: 120 }}
                                value={row.value ?? ''} onChange={e => onRowChange(idx, 'value', parseFloat(e.target.value) || 0)} /></td>
                            <td className="mono faint">{row.unit}</td>
                            <td className="r num faint">{row.page ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

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

    useEffect(() => {
        fetch(`/api/reference/orders?order_type=${orderType}`).then(r => r.json()).then(d => setOrders(d.orders || [])).catch(() => {})
    }, [orderType, saveStatus])

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

    const handleRowChange = (idx, field, value) => setEditableRows(rows => rows.map((r, i) => i === idx ? { ...r, [field]: value } : r))

    const handleConfirm = async () => {
        if (!extracted) return
        setSaveStatus('Saving…')
        try {
            const res = await fetch('/api/reference/orders/confirm', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: extracted.order_id, order_type: orderType, order_number: extracted.order_number || orderNumber, control_period: extracted.control_period || '', document_type: extracted.document_type || orderType, confirmed_rows: editableRows }),
            })
            const d = await res.json(); setSaveStatus(d.message || 'Saved')
            setExtracted(null); setEditableRows([]); setFile(null)
            if (fileRef.current) fileRef.current.value = ''
        } catch (e) { setSaveStatus('Error: ' + e.message) }
    }

    return (
        <div className="stack">
            <div>
                <p className="h3">{label}</p>
                <p className="muted" style={{ marginTop: 4, maxWidth: '72ch' }}>{description}</p>
            </div>
            <div className="row" style={{ alignItems: 'flex-end' }}>
                <input ref={fileRef} type="file" accept=".pdf" hidden onChange={e => setFile(e.target.files[0])} />
                <button className="btn" onClick={() => fileRef.current?.click()} style={{ maxWidth: 360 }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{file ? file.name : 'Choose PDF…'}</span>
                    {file && <span className="faint num">{(file.size / 1024).toFixed(0)} KB</span>}
                </button>
                <input type="text" placeholder="Order no." className="input" style={{ width: 160 }} value={orderNumber} onChange={e => setOrderNumber(e.target.value)} />
                {orderType === 'past_order' && (
                    <>
                        <select className="select" style={{ width: 160 }} value={licensee} onChange={e => setLicensee(e.target.value)}>
                            <option value="">Licensee</option>{LICENSEES.map(l => <option key={l}>{l}</option>)}
                        </select>
                        <select className="select" style={{ width: 130 }} value={financialYear} onChange={e => setFinancialYear(e.target.value)}>
                            <option value="">Year</option>{FINANCIAL_YEARS.map(y => <option key={y}>{y}</option>)}
                        </select>
                    </>
                )}
                <button className="btn btn-accent" disabled={!file || loading} onClick={handleUpload}>{loading ? 'Extracting…' : 'Upload & extract'}</button>
            </div>
            {error && <Notice tone="bad" onClose={() => setError(null)}>{error}</Notice>}

            {extracted && editableRows.length > 0 && (
                <div className="card view">
                    <div className="card-head"><span className="h3">Extracted {editableRows.length} values</span><span className="spacer" /><span className="label">Review before saving</span></div>
                    <ExtractionReviewTable rows={editableRows} onRowChange={handleRowChange} />
                    <div className="row card-body" style={{ borderTop: '1px solid var(--line)' }}>
                        <button className="btn btn-accent" onClick={handleConfirm}>Confirm & save</button>
                        <button className="btn btn-ghost" onClick={() => { setExtracted(null); setEditableRows([]) }}>Cancel</button>
                    </div>
                </div>
            )}
            {saveStatus && <Notice tone={saveStatus.startsWith('Error') ? 'bad' : 'ok'}>{saveStatus}</Notice>}

            {orders.length > 0 && (
                <div className="card">
                    <div className="card-head"><span className="h3">Uploaded orders</span><span className="faint num">{orders.length}</span></div>
                    <div className="table-wrap"><table className="table"><tbody>
                        {orders.map(o => (
                            <tr key={o.id}><td style={{ fontWeight: 500 }}>{o.order_number || 'Unnamed'}</td><td className="muted">{o.licensee}</td><td className="num faint">{o.financial_year}</td></tr>
                        ))}
                    </tbody></table></div>
                </div>
            )}
        </div>
    )
}

function EconomicIndicatorsSection() {
    const [indicators, setIndicators] = useState([])
    const [editing, setEditing] = useState({})
    const [saveStatus, setSaveStatus] = useState({})
    const blank = { financial_year: '', wpi_pct: '', cpi_pct: '', sbi_plr_pct: '', hsd_price_rs: '', power_purchase_rate_rs_per_kwh: '' }
    const [newRow, setNewRow] = useState(blank)

    useEffect(() => {
        fetch('/api/reference/economic-indicators').then(r => r.json()).then(d => setIndicators(d.indicators || [])).catch(() => {})
    }, [saveStatus])

    const handleSave = async (row) => {
        try {
            await fetch('/api/reference/economic-indicators', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(row) })
            setSaveStatus(s => ({ ...s, [row.financial_year]: 'Saved' }))
            setTimeout(() => setSaveStatus(s => { const n = { ...s }; delete n[row.financial_year]; return n }), 2000)
        } catch { setSaveStatus(s => ({ ...s, [row.financial_year]: 'Failed' })) }
    }

    const handleAddNew = async () => {
        if (!newRow.financial_year) return
        const n = (k) => parseFloat(newRow[k]) || null
        await handleSave({ financial_year: newRow.financial_year, wpi_pct: n('wpi_pct'), cpi_pct: n('cpi_pct'), sbi_plr_pct: n('sbi_plr_pct'), hsd_price_rs: n('hsd_price_rs'), power_purchase_rate_rs_per_kwh: n('power_purchase_rate_rs_per_kwh') })
        setNewRow(blank)
    }

    const stopEdit = (fy) => setEditing(e => { const n = { ...e }; delete n[fy]; return n })
    const cols = [
        { key: 'wpi_pct', label: 'WPI %' }, { key: 'cpi_pct', label: 'CPI %' }, { key: 'sbi_plr_pct', label: 'SBI PLR %' },
        { key: 'hsd_price_rs', label: 'HSD ₹/L' }, { key: 'power_purchase_rate_rs_per_kwh', label: 'PPC ₹/kWh' },
    ]

    return (
        <div className="stack">
            <p className="muted">Indicators per financial year, used by the auditor for O&amp;M escalation.</p>
            <div className="card table-wrap">
                <table className="table">
                    <thead><tr><th>Year</th>{cols.map(c => <th key={c.key} className="r">{c.label}</th>)}<th className="r" style={{ width: 170 }} /></tr></thead>
                    <tbody>
                        {indicators.map(row => {
                            const isE = editing[row.financial_year]; const eR = isE || row
                            return (
                                <tr key={row.financial_year}>
                                    <td className="num" style={{ fontWeight: 600 }}>{row.financial_year}</td>
                                    {cols.map(c => (
                                        <td key={c.key} className="r">
                                            {isE
                                                ? <input type="number" step="any" className="input input-sm num" style={{ width: 90 }} value={eR[c.key] ?? ''}
                                                    onChange={e => setEditing(ed => ({ ...ed, [row.financial_year]: { ...eR, [c.key]: e.target.value } }))} />
                                                : <span className="num">{row[c.key] ?? <span className="faint">—</span>}</span>}
                                        </td>
                                    ))}
                                    <td className="r">
                                        {isE ? (
                                            <span className="row" style={{ justifyContent: 'flex-end' }}>
                                                <button className="btn btn-sm btn-accent" onClick={() => { handleSave({ financial_year: row.financial_year, ...eR }); stopEdit(row.financial_year) }}>Save</button>
                                                <button className="btn btn-sm btn-ghost" onClick={() => stopEdit(row.financial_year)}>Cancel</button>
                                            </span>
                                        ) : (
                                            <span className="row" style={{ justifyContent: 'flex-end' }}>
                                                {saveStatus[row.financial_year] && <span className={`pill ${saveStatus[row.financial_year] === 'Saved' ? 'pill-ok' : 'pill-bad'}`}>{saveStatus[row.financial_year]}</span>}
                                                <button className="btn btn-sm" onClick={() => setEditing(e => ({ ...e, [row.financial_year]: { ...row } }))}>Edit</button>
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            )
                        })}
                        <tr>
                            <td>
                                <select className="select input-sm" style={{ width: 120 }} value={newRow.financial_year} onChange={e => setNewRow(r => ({ ...r, financial_year: e.target.value }))}>
                                    <option value="">Add year</option>
                                    {FINANCIAL_YEARS.filter(y => !indicators.find(i => i.financial_year === y)).map(y => <option key={y}>{y}</option>)}
                                </select>
                            </td>
                            {cols.map(c => (
                                <td key={c.key} className="r"><input type="number" step="any" placeholder="0" className="input input-sm num" style={{ width: 90 }}
                                    value={newRow[c.key]} onChange={e => setNewRow(r => ({ ...r, [c.key]: e.target.value }))} /></td>
                            ))}
                            <td className="r"><button className="btn btn-sm btn-accent" disabled={!newRow.financial_year} onClick={handleAddNew}>Add</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

function MYTNormsSection() {
    const [baselines, setBaselines] = useState({})
    const [selectedLicensee, setSelectedLicensee] = useState('Infopark')
    const [selectedYear, setSelectedYear] = useState('2024-25')
    const [editing, setEditing] = useState(false)
    const [editValues, setEditValues] = useState({})
    const [saveStatus, setSaveStatus] = useState(null)

    useEffect(() => {
        fetch('/api/reference/myt-baselines').then(r => r.json()).then(d => setBaselines(d.baselines || {})).catch(() => {})
    }, [saveStatus])

    const currentNorms = baselines[selectedLicensee]?.baselines?.[selectedYear] || {}
    const availableYears = baselines[selectedLicensee] ? Object.keys(baselines[selectedLicensee]?.baselines || {}) : FINANCIAL_YEARS

    const handleSave = async () => {
        const rows = Object.entries(editValues).map(([k, v]) => ({ field_key: k, licensee: selectedLicensee, year: selectedYear, value: parseFloat(v) || 0, field: k, unit: 'Rs Lakhs' }))
        try {
            const res = await fetch('/api/reference/orders/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: 'manual', order_type: 'myt_order', order_number: '', control_period: '', document_type: 'MANUAL_EDIT', confirmed_rows: rows }) })
            const d = await res.json(); setSaveStatus(d.message || 'Saved'); setEditing(false)
        } catch (e) { setSaveStatus('Error: ' + e.message) }
    }

    return (
        <div className="stack">
            <p className="muted">MYT baselines per licensee. Overrides apply to every subsequent audit.</p>
            <div className="row">
                <div className="segmented">
                    {LICENSEES.map(l => <button key={l} className={selectedLicensee === l ? 'is-active' : ''} onClick={() => setSelectedLicensee(l)}>{l}</button>)}
                </div>
                <span className="spacer" />
                <select className="select" style={{ width: 140 }} value={selectedYear} onChange={e => setSelectedYear(e.target.value)}>
                    {availableYears.map(y => <option key={y}>{y}</option>)}
                </select>
            </div>

            {Object.keys(currentNorms).length > 0 ? (
                <div className="card table-wrap">
                    <table className="table">
                        <thead><tr><th>Field</th><th className="r">Value</th><th>Unit</th></tr></thead>
                        <tbody>
                            {Object.entries(currentNorms).map(([key, val]) => {
                                const unit = key.includes('pct') || key.includes('loss') ? '%' : key.includes('rs_per_kwh') ? 'Rs/kWh' : 'Rs Lakhs'
                                return (
                                    <tr key={key}>
                                        <td style={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</td>
                                        <td className="r">
                                            {editing
                                                ? <input type="number" step="any" defaultValue={val} className="input input-sm num" style={{ width: 130 }} onChange={e => setEditValues(v => ({ ...v, [key]: e.target.value }))} />
                                                : <span className="num" style={{ fontWeight: 600 }}>{val}</span>}
                                        </td>
                                        <td className="mono faint">{unit}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="card empty">No norms recorded for {selectedLicensee} · FY {selectedYear}</div>
            )}
            <div className="row">
                {editing ? <>
                    <button className="btn btn-accent" onClick={handleSave}>Save norms</button>
                    <button className="btn btn-ghost" onClick={() => { setEditing(false); setEditValues({}) }}>Cancel</button>
                </> : <button className="btn" onClick={() => { setEditing(true); setEditValues({}) }}>Edit norms</button>}
                {saveStatus && <span className={`pill ${saveStatus.startsWith('Error') ? 'pill-bad' : 'pill-ok'}`}>{saveStatus}</span>}
            </div>
        </div>
    )
}

export default function ReferenceDataPage() {
    const [activeTab, setActiveTab] = useState('economic')

    return (
        <section className="stack view">
            <PageHead eyebrow="Reference" title="Reference data"
                lede="Economic indicators, MYT norms and reference orders. Changes apply to every audit run." />
            <div className="tabs enter-panel">
                {TABS.map((t, i) => (
                    <button key={t.id} className={`tab ${activeTab === t.id ? 'is-active' : ''}`} onClick={() => setActiveTab(t.id)}>
                        <span className="num">{String(i + 1).padStart(2, '0')}</span>{t.label}
                    </button>
                ))}
            </div>
            <div className="view" key={activeTab}>
                {activeTab === 'economic' && <EconomicIndicatorsSection />}
                {activeTab === 'myt' && <MYTNormsSection />}
                {activeTab === 'interim' && <PDFUploadSection orderType="interim_tariff" label="MYT or interim tariff order" description="The model reads the order and extracts every ARR component norm across the control period. Review the values before saving." />}
                {activeTab === 'past' && <PDFUploadSection orderType="past_order" label="Finalized truing-up order" description="Approved amounts are extracted and stored as precedent for future audits and the analyst." />}
            </div>
        </section>
    )
}
