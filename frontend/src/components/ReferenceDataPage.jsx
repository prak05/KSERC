import React, { useState, useEffect, useRef } from 'react'

// ─── Section Tabs ────────────────────────────────────────────────────
const TABS = [
    { id: 'economic', label: '📊 Economic Indicators' },
    { id: 'myt', label: '📋 MYT Norms' },
    { id: 'interim', label: '📄 MYT / Interim Tariff Orders' },
    { id: 'past', label: '📁 Past Accepted Orders' },
]

const LICENSEES = ['Technopark', 'Infopark', 'CSEZA', 'KDHP']
const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

// ─── Extraction Table: shows Gemini-extracted rows, editable ─────────
function ExtractionReviewTable({ rows, onRowChange }) {
    if (!rows || rows.length === 0) return (
        <p className="text-white/40 italic text-sm mt-3 bg-black/20 p-4 rounded-xl border border-white/5 text-center">No data extracted yet.</p>
    )
    return (
        <div className="overflow-x-auto rounded-xl border border-white/10 mt-4 shadow-lg">
            <table className="w-full text-sm font-mono text-left">
                <thead>
                    <tr className="bg-black/40 text-white/50 text-[10px] uppercase tracking-widest border-b border-white/10">
                        <th className="px-4 py-3 font-bold text-center">Sl.</th>
                        <th className="px-5 py-3 font-bold font-sans">Licensee</th>
                        <th className="px-5 py-3 font-bold">Year</th>
                        <th className="px-5 py-3 font-bold font-sans">Field</th>
                        <th className="px-5 py-3 font-bold text-right">Value</th>
                        <th className="px-5 py-3 font-bold">Unit</th>
                        <th className="px-5 py-3 font-bold text-center">Page</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, idx) => (
                        <tr key={idx} className={`border-b border-white/5 transition-colors hover:bg-white/5 ${idx % 2 === 0 ? 'bg-black/20' : 'bg-transparent'}`}>
                            <td className="px-4 py-3 text-white/30 text-center">{String(idx + 1).padStart(2, '0')}</td>
                            <td className="px-5 py-3 text-white/90 font-sans font-semibold">{row.licensee}</td>
                            <td className="px-5 py-3 text-white/70">{row.year}</td>
                            <td className="px-5 py-3 text-white/80 font-sans">{row.field}</td>
                            <td className="px-5 py-3 text-right">
                                <input
                                    type="number"
                                    step="any"
                                    value={row.value ?? ''}
                                    onChange={e => onRowChange(idx, 'value', parseFloat(e.target.value) || 0)}
                                    className="w-28 text-right bg-black/40 border border-emerald-500/50 rounded px-2 py-1 text-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-500 shadow-inner"
                                />
                            </td>
                            <td className="px-5 py-3 text-white/50">{row.unit}</td>
                            <td className="px-5 py-3 text-center text-white/40">{row.page ?? '—'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

// ─── Upload + Extract + Confirm component ────────────────────────────
function PDFUploadSection({ orderType, label, description }) {
    const [file, setFile] = useState(null)
    const [orderNumber, setOrderNumber] = useState('')
    const [licensee, setLicensee] = useState('')
    const [financialYear, setFinancialYear] = useState('')
    const [loading, setLoading] = useState(false)
    const [extracted, setExtracted] = useState(null)  // { order_id, rows, order_number, control_period, document_type }
    const [editableRows, setEditableRows] = useState([])
    const [saveStatus, setSaveStatus] = useState(null)
    const [error, setError] = useState(null)
    const [orders, setOrders] = useState([])
    const fileRef = useRef()

    useEffect(() => { fetchOrders() }, [saveStatus])

    const fetchOrders = async () => {
        try {
            const res = await fetch(`/api/reference/orders?order_type=${orderType}`)
            const data = await res.json()
            setOrders(data.orders || [])
        } catch { }
    }

    const handleUpload = async () => {
        if (!file) return
        setLoading(true)
        setError(null)
        setSaveStatus(null)

        const form = new FormData()
        form.append('file', file)
        form.append('order_type', orderType)
        form.append('order_number', orderNumber)
        form.append('licensee', licensee)
        form.append('financial_year', financialYear)

        try {
            const res = await fetch('/api/reference/orders/extract', { method: 'POST', body: form })
            if (!res.ok) throw new Error('Extraction failed')
            const data = await res.json()
            setExtracted(data)
            setEditableRows(data.extracted_rows || [])
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    const handleRowChange = (idx, field, value) => {
        const updated = [...editableRows]
        updated[idx] = { ...updated[idx], [field]: value }
        setEditableRows(updated)
    }

    const handleConfirm = async () => {
        if (!extracted) return
        setSaveStatus('saving')
        try {
            const res = await fetch('/api/reference/orders/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    order_id: extracted.order_id,
                    order_type: orderType,
                    order_number: extracted.order_number || orderNumber,
                    control_period: extracted.control_period || '',
                    document_type: extracted.document_type || orderType,
                    confirmed_rows: editableRows,
                }),
            })
            const data = await res.json()
            setSaveStatus(data.message || 'Saved!')
            setExtracted(null)
            setEditableRows([])
            setFile(null)
            if (fileRef.current) fileRef.current.value = ''
        } catch (e) {
            setSaveStatus('Error: ' + e.message)
        }
    }

    return (
        <div className="space-y-6">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 md:p-8 space-y-6 shadow-lg backdrop-blur-sm relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-kserc-blue to-kserc-blue-dark opacity-50 group-hover:opacity-100 transition-opacity" />

                <div>
                    <h3 className="font-bold text-white tracking-wide text-lg">{label}</h3>
                    <p className="text-white/60 text-sm mt-1 leading-relaxed">{description}</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf"
                        onChange={e => setFile(e.target.files[0])}
                        className="col-span-1 sm:col-span-2 text-sm text-white/70 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-kserc-blue/20 file:text-kserc-blue hover:file:bg-kserc-blue hover:file:text-white file:transition-all hover:file:shadow-[0_0_15px_rgba(59,130,246,0.3)] cursor-pointer bg-black/20 border border-white/10 rounded-xl px-4 py-2 focus:outline-none focus:ring-1 focus:ring-kserc-blue"
                    />
                    <input
                        type="text"
                        placeholder="Order Number (e.g. OP 09/2023)"
                        value={orderNumber}
                        onChange={e => setOrderNumber(e.target.value)}
                        className="px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-sm text-white placeholder-white/30 focus:outline-none focus:border-kserc-blue focus:ring-1 focus:ring-kserc-blue transition-all"
                    />
                    {orderType === 'past_order' && (
                        <select
                            value={financialYear}
                            onChange={e => setFinancialYear(e.target.value)}
                            className="px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-kserc-blue focus:ring-1 focus:ring-kserc-blue transition-all"
                        >
                            <option value="" className="bg-gray-900 text-white">Financial Year</option>
                            {FINANCIAL_YEARS.map(y => <option key={y} value={y} className="bg-gray-900 text-white">{y}</option>)}
                        </select>
                    )}
                </div>

                <div className="pt-2">
                    <button
                        onClick={handleUpload}
                        disabled={!file || loading}
                        className="px-6 py-3 bg-kserc-blue hover:bg-kserc-blue-dark disabled:opacity-40 disabled:hover:scale-100 text-white rounded-xl text-sm font-bold tracking-wide transition-all shadow-[0_0_15px_rgba(59,130,246,0.2)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:-translate-y-0.5 w-full sm:w-auto flex items-center justify-center gap-2"
                    >
                        {loading ? <span className="animate-pulse">⏳ Gemini Extracting…</span> : <span>📤 Upload & Extract</span>}
                    </button>
                    {error && <p className="text-red-400 text-sm mt-3 ml-1">⚠️ {error}</p>}
                </div>
            </div>

            {/* Extracted Table — editable before confirm */}
            {extracted && editableRows.length > 0 && (
                <div className="bg-emerald-500/5 border border-emerald-500/30 rounded-2xl p-6 md:p-8 space-y-4 shadow-[0_0_30px_rgba(16,185,129,0.05)] backdrop-blur-md animate-fade-in-up">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-emerald-500/20 pb-4">
                        <h4 className="text-emerald-400 font-bold text-lg flex items-center gap-2">
                            <span>✅</span>
                            <span>Gemini Extracted {editableRows.length} values</span>
                            {extracted.order_number && <span className="ml-2 bg-emerald-500/10 px-2 py-0.5 rounded text-emerald-300 font-mono text-sm border border-emerald-500/20">{extracted.order_number}</span>}
                        </h4>
                        <span className="text-emerald-500/60 text-xs font-bold uppercase tracking-widest bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">Edit cells before confirming ↓</span>
                    </div>
                    <ExtractionReviewTable rows={editableRows} onRowChange={handleRowChange} />
                    <div className="flex flex-wrap items-center gap-4 pt-4">
                        <button
                            onClick={handleConfirm}
                            className="px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-white rounded-xl text-sm font-bold tracking-wide transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] hover:-translate-y-0.5 flex items-center gap-2"
                        >
                            <span>✔</span> Confirm & Save to System
                        </button>
                        <button
                            onClick={() => { setExtracted(null); setEditableRows([]) }}
                            className="px-6 py-3 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white border border-white/10 rounded-xl text-sm font-semibold transition-all hover:-translate-y-0.5"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {saveStatus && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-5 py-3.5 text-emerald-300 text-sm font-bold flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                    <span>✨</span> {saveStatus}
                </div>
            )}

            {/* Orders list */}
            {orders.length > 0 && (
                <div className="bg-black/20 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
                    <h4 className="text-white font-bold tracking-wide mb-4 text-base flex items-center gap-2">
                        <span>📁</span> Uploaded Orders
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {orders.map(o => (
                            <div key={o.id} className="flex flex-col gap-1 bg-white/5 border border-white/5 hover:border-white/20 transition-colors rounded-xl p-4">
                                <span className="text-white font-bold text-sm truncate">{o.order_number || 'Unnamed Order'}</span>
                                <div className="flex items-center gap-2 text-[11px] font-mono text-white/50 uppercase tracking-widest mt-1">
                                    {o.licensee && <span>{o.licensee}</span>}
                                    {o.licensee && o.financial_year && <span>•</span>}
                                    {o.financial_year && <span>{o.financial_year}</span>}
                                </div>
                                <span className="text-white/30 text-[10px] mt-2 bg-black/20 self-start px-2 py-0.5 rounded border border-white/5">
                                    {new Date(o.uploaded_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

// ─── Economic Indicators Section ─────────────────────────────────────
function EconomicIndicatorsSection() {
    const [indicators, setIndicators] = useState([])
    const [editing, setEditing] = useState({})
    const [saveStatus, setSaveStatus] = useState({})
    const [newRow, setNewRow] = useState({ financial_year: '', wpi_pct: '', cpi_pct: '', sbi_plr_pct: '', hsd_price_rs: '', power_purchase_rate_rs_per_kwh: '' })

    useEffect(() => {
        fetch('/api/reference/economic-indicators')
            .then(r => r.json())
            .then(d => setIndicators(d.indicators || []))
            .catch(() => { })
    }, [saveStatus])

    const handleSave = async (row) => {
        try {
            const res = await fetch('/api/reference/economic-indicators', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(row),
            })
            const data = await res.json()
            setSaveStatus(s => ({ ...s, [row.financial_year]: '✓ Saved' }))
            setTimeout(() => setSaveStatus(s => { const n = { ...s }; delete n[row.financial_year]; return n }), 2000)
        } catch (e) {
            setSaveStatus(s => ({ ...s, [row.financial_year]: 'Error' }))
        }
    }

    const handleAddNew = async () => {
        if (!newRow.financial_year) return
        await handleSave({
            financial_year: newRow.financial_year,
            wpi_pct: parseFloat(newRow.wpi_pct) || null,
            cpi_pct: parseFloat(newRow.cpi_pct) || null,
            sbi_plr_pct: parseFloat(newRow.sbi_plr_pct) || null,
            hsd_price_rs: parseFloat(newRow.hsd_price_rs) || null,
            power_purchase_rate_rs_per_kwh: parseFloat(newRow.power_purchase_rate_rs_per_kwh) || null,
        })
        setNewRow({ financial_year: '', wpi_pct: '', cpi_pct: '', sbi_plr_pct: '', hsd_price_rs: '', power_purchase_rate_rs_per_kwh: '' })
    }

    const cols = [
        { key: 'wpi_pct', label: 'WPI %' },
        { key: 'cpi_pct', label: 'CPI %' },
        { key: 'sbi_plr_pct', label: 'SBI PLR %' },
        { key: 'hsd_price_rs', label: 'HSD Price (₹/L)' },
        { key: 'power_purchase_rate_rs_per_kwh', label: 'Avg PPC (₹/kWh)' },
    ]

    return (
        <div className="space-y-6">
            <p className="text-white/60 text-sm leading-relaxed max-w-3xl">
                Enter economic indicators per financial year. These are automatically fetched by the auditor via RAG for O&amp;M escalation calculations.
            </p>

            <div className="overflow-x-auto rounded-xl border border-white/10 shadow-xl bg-black/20">
                <table className="w-full text-sm font-mono">
                    <thead>
                        <tr className="bg-black/40 text-white/50 text-[10px] uppercase tracking-widest border-b border-white/10">
                            <th className="px-5 py-4 text-left font-bold font-sans">Financial Year</th>
                            {cols.map(c => <th key={c.key} className="px-5 py-4 text-right font-bold">{c.label}</th>)}
                            <th className="px-5 py-4 text-center font-bold">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {indicators.map((row, idx) => {
                            const isEditing = editing[row.financial_year]
                            const editRow = isEditing || row
                            return (
                                <tr key={row.financial_year} className={`border-b border-white/5 transition-colors hover:bg-white/5 ${idx % 2 === 0 ? 'bg-black/10' : 'bg-transparent'}`}>
                                    <td className="px-5 py-4 text-white font-bold text-base">{row.financial_year}</td>
                                    {cols.map(c => (
                                        <td key={c.key} className="px-5 py-4 text-right">
                                            {isEditing ? (
                                                <input
                                                    type="number" step="any"
                                                    value={editRow[c.key] ?? ''}
                                                    onChange={e => setEditing(ed => ({ ...ed, [row.financial_year]: { ...editRow, [c.key]: e.target.value } }))}
                                                    className="w-24 text-right bg-black/40 border border-kserc-blue/50 rounded px-2 py-1 text-kserc-blue focus:outline-none focus:ring-1 focus:ring-kserc-blue shadow-inner"
                                                />
                                            ) : (
                                                <span className="text-white/80">{row[c.key] ?? <span className="text-white/20">—</span>}</span>
                                            )}
                                        </td>
                                    ))}
                                    <td className="px-5 py-4 text-center">
                                        {isEditing ? (
                                            <div className="flex gap-2 justify-center">
                                                <button onClick={() => { handleSave({ financial_year: row.financial_year, ...editRow }); setEditing(e => { const n = { ...e }; delete n[row.financial_year]; return n }) }}
                                                    className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded shadow-[0_0_10px_rgba(16,185,129,0.3)] transition-all text-xs font-bold uppercase tracking-wider">Save</button>
                                                <button onClick={() => setEditing(e => { const n = { ...e }; delete n[row.financial_year]; return n })}
                                                    className="px-4 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded transition-colors text-xs font-bold uppercase tracking-wider">Cancel</button>
                                            </div>
                                        ) : (
                                            <div className="flex gap-3 justify-center items-center">
                                                <button onClick={() => setEditing(e => ({ ...e, [row.financial_year]: { ...row } }))}
                                                    className="px-4 py-1.5 bg-kserc-blue/20 hover:bg-kserc-blue text-white border border-kserc-blue/50 hover:border-kserc-blue rounded shadow-[0_0_10px_rgba(59,130,246,0.1)] transition-all text-xs font-bold uppercase tracking-wider">Edit</button>
                                                {saveStatus[row.financial_year] && <span className="text-emerald-400 text-xs font-semibold bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">{saveStatus[row.financial_year]}</span>}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            )
                        })}

                        {/* New row */}
                        <tr className="border-t-2 border-kserc-blue/30 bg-kserc-blue/5 relative">
                            <td className="px-5 py-5 relative z-10">
                                <select value={newRow.financial_year} onChange={e => setNewRow(r => ({ ...r, financial_year: e.target.value }))}
                                    className="bg-black/50 border border-kserc-blue/50 rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:ring-1 focus:ring-kserc-blue shadow-inner w-full font-sans">
                                    <option value="" className="bg-gray-900">+ Add Year</option>
                                    {FINANCIAL_YEARS.filter(y => !indicators.find(i => i.financial_year === y)).map(y => <option key={y} value={y} className="bg-gray-900">{y}</option>)}
                                </select>
                            </td>
                            {cols.map(c => (
                                <td key={c.key} className="px-5 py-5 text-right relative z-10">
                                    <input type="number" step="any" placeholder="0.0"
                                        value={newRow[c.key]}
                                        onChange={e => setNewRow(r => ({ ...r, [c.key]: e.target.value }))}
                                        className="w-24 text-right bg-black/50 border border-white/20 rounded-lg px-2 py-1.5 text-white focus:border-kserc-blue focus:outline-none focus:ring-1 focus:ring-kserc-blue placeholder-white/30 shadow-inner"
                                    />
                                </td>
                            ))}
                            <td className="px-5 py-5 text-center relative z-10">
                                <button onClick={handleAddNew} disabled={!newRow.financial_year}
                                    className="px-5 py-2 w-full bg-kserc-blue hover:bg-kserc-blue-dark disabled:opacity-40 disabled:hover:scale-100 disabled:shadow-none text-white rounded-lg text-xs font-black uppercase tracking-widest shadow-[0_0_15px_rgba(59,130,246,0.5)] transition-all hover:-translate-y-0.5">
                                    Add
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// ─── MYT Norms Viewer + Editor ────────────────────────────────────────
function MYTNormsSection() {
    const [baselines, setBaselines] = useState({})
    const [selectedLicensee, setSelectedLicensee] = useState('Infopark')
    const [selectedYear, setSelectedYear] = useState('2024-25')
    const [editing, setEditing] = useState(false)
    const [editValues, setEditValues] = useState({})
    const [saveStatus, setSaveStatus] = useState(null)

    useEffect(() => {
        fetch('/api/reference/myt-baselines')
            .then(r => r.json())
            .then(d => setBaselines(d.baselines || {}))
            .catch(() => { })
    }, [saveStatus])

    const currentNorms = baselines[selectedLicensee]?.baselines?.[selectedYear] || {}
    const availableYears = selectedLicensee && baselines[selectedLicensee]
        ? Object.keys(baselines[selectedLicensee]?.baselines || {})
        : FINANCIAL_YEARS

    const handleSave = async () => {
        const confirmed_rows = Object.entries(editValues).map(([field_key, value]) => ({
            field_key, licensee: selectedLicensee, year: selectedYear, value: parseFloat(value) || 0,
            field: field_key, unit: 'Rs Lakhs',
        }))
        try {
            const res = await fetch('/api/reference/orders/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: 'manual', order_type: 'myt_order', order_number: '', control_period: '', document_type: 'MANUAL_EDIT', confirmed_rows }),
            })
            const data = await res.json()
            setSaveStatus(data.message || 'Saved')
            setEditing(false)
        } catch (e) { setSaveStatus('Error: ' + e.message) }
    }

    return (
        <div className="space-y-6">
            <p className="text-white/60 text-sm leading-relaxed max-w-3xl">View and edit MYT baseline norms per licensee and year. Overrides are saved and apply immediately to audits referencing these periods.</p>

            <div className="flex gap-4 flex-wrap bg-black/20 p-2 rounded-2xl border border-white/5 backdrop-blur-sm">
                <div className="flex bg-white/5 rounded-xl p-1 shadow-inner gap-1">
                    {LICENSEES.map(l => (
                        <button key={l} onClick={() => setSelectedLicensee(l)}
                            className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${selectedLicensee === l ? 'bg-kserc-blue text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]' : 'text-white/50 hover:text-white hover:bg-white/10'}`}>
                            {l}
                        </button>
                    ))}
                </div>
                <select value={selectedYear} onChange={e => setSelectedYear(e.target.value)}
                    className="px-5 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm font-bold text-white focus:outline-none focus:ring-1 focus:ring-kserc-blue hover:bg-white/10 transition-colors ml-auto shadow-inner min-w-[120px]">
                    {availableYears.map(y => <option key={y} value={y} className="bg-gray-900 text-white font-sans">{y}</option>)}
                </select>
            </div>

            {Object.keys(currentNorms).length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-white/10 shadow-xl bg-black/20">
                    <table className="w-full text-sm font-mono">
                        <thead>
                            <tr className="bg-black/40 text-white/50 text-[10px] uppercase tracking-widest border-b border-white/10">
                                <th className="px-5 py-4 text-left font-bold font-sans">Field</th>
                                <th className="px-5 py-4 text-right font-bold">Value</th>
                                <th className="px-5 py-4 text-left font-bold pl-8">Unit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(currentNorms).map(([key, val], idx) => {
                                const unit = key.includes('pct') || key.includes('loss') ? '%' : key.includes('rs_per_kwh') ? 'Rs/kWh' : 'Rs Lakhs'
                                return (
                                    <tr key={key} className={`border-b border-white/5 transition-colors hover:bg-white/5 ${idx % 2 === 0 ? 'bg-black/10' : 'bg-transparent'}`}>
                                        <td className="px-5 py-4 text-white/80 font-sans font-semibold capitalize tracking-wide">{key.replace(/_/g, ' ')}</td>
                                        <td className="px-5 py-4 text-right">
                                            {editing ? (
                                                <input type="number" step="any" defaultValue={val}
                                                    onChange={e => setEditValues(v => ({ ...v, [key]: e.target.value }))}
                                                    className="w-32 text-right bg-black/40 border border-kserc-blue/50 rounded px-2 py-1.5 text-kserc-blue focus:outline-none focus:ring-1 focus:ring-kserc-blue shadow-inner" />
                                            ) : (
                                                <span className="text-emerald-400 font-bold drop-shadow-md text-base">{val}</span>
                                            )}
                                        </td>
                                        <td className="px-5 pl-8 py-4 text-white/40">{unit}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="text-white/40 italic text-sm bg-black/20 rounded-2xl p-8 border border-white/5 text-center shadow-inner">
                    <span className="text-4xl block mb-3 opacity-50">📂</span>
                    No norms found for <strong className="text-white/70">{selectedLicensee}</strong> ({selectedYear}). Upload an MYT order above to populate.
                </div>
            )}

            <div className="flex gap-4 items-center pt-2">
                {editing ? (
                    <>
                        <button onClick={handleSave} className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded-xl text-sm font-bold shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all hover:-translate-y-0.5">✔ Save Changes</button>
                        <button onClick={() => { setEditing(false); setEditValues({}) }} className="px-6 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white rounded-xl text-sm font-bold transition-all">Cancel</button>
                    </>
                ) : (
                    <button onClick={() => { setEditing(true); setEditValues({}) }} className="px-6 py-2.5 bg-kserc-blue/20 hover:bg-kserc-blue border border-kserc-blue/50 text-white rounded-xl text-sm font-bold shadow-[0_0_15px_rgba(59,130,246,0.2)] hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] transition-all flex items-center gap-2">
                        <span>✏️</span> Edit Values
                    </button>
                )}
                {saveStatus && <span className="text-emerald-400 text-sm font-bold bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]">{saveStatus}</span>}
            </div>
        </div>
    )
}

// ─── Main ReferenceDataPage ───────────────────────────────────────────
export default function ReferenceDataPage() {
    const [activeTab, setActiveTab] = useState('economic')

    return (
        <div className="animate-fade-in-up space-y-8 max-w-[1400px] mx-auto">
            {/* Header */}
            <div>
                <h2 className="text-3xl font-bold text-white tracking-tight drop-shadow-md">Reference Data Management</h2>
                <p className="text-white/60 mt-2 text-base max-w-3xl">
                    Manage external inputs used by the analysis pipeline — economic indicators, MYT norms, and uploaded reference orders. These dynamically affect all subsequent audit runs.
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-black/40 backdrop-blur-xl rounded-2xl p-1.5 border border-white/10 shadow-inner overflow-x-auto custom-scrollbar">
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex-1 min-w-[180px] px-6 py-3.5 rounded-xl text-sm font-bold transition-all relative overflow-hidden group ${activeTab === tab.id
                            ? 'bg-kserc-blue/20 border border-kserc-blue/50 text-white shadow-[0_0_20px_rgba(59,130,246,0.2)]'
                            : 'text-white/50 hover:text-white hover:bg-white/5 border border-transparent'
                            }`}
                    >
                        <span className="relative z-10 flex items-center justify-center gap-2">{tab.label}</span>
                        {activeTab === tab.id && (
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-kserc-blue/10 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
                        )}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="bg-kserc-surface/60 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 md:p-10 shadow-2xl relative overflow-hidden transition-all duration-500 min-h-[500px]">
                <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

                <div className="animate-fade-in-up" key={activeTab}>
                    {activeTab === 'economic' && <EconomicIndicatorsSection />}

                    {activeTab === 'myt' && <MYTNormsSection />}

                    {activeTab === 'interim' && (
                        <PDFUploadSection
                            orderType="interim_tariff"
                            label="Upload MYT / Mid-Term Review / Interim Tariff Order"
                            description="Upload a KSERC MYT Order, Mid-Term Performance Review (MPR), or Interim Tariff Order. Gemini will intelligently extract ALL ARR component norms across all financial years in the document, instantly making them available to the audit pipeline."
                        />
                    )}

                    {activeTab === 'past' && (
                        <PDFUploadSection
                            orderType="past_order"
                            label="Upload Finalized KSERC Truing-Up Order"
                            description="Upload an accepted/finalized KSERC Truing-Up order. Gemini extracts approved amounts for precedence. These are embedded and stored in the RAG knowledgebase."
                        />
                    )}
                </div>
            </div>
        </div>
    )
}
