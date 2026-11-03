import { useRef, useState } from 'react'
import { Cta } from './ui'

const LICENSEES = [
    { value: 'Technopark', label: 'Technopark' },
    { value: 'Infopark', label: 'Infopark' },
    { value: 'CSEZ', label: 'CSEZA' },
    { value: 'KDHP', label: 'KDHP' },
]

const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23']

const PARAMS = [
    { key: 'inflation_pct', label: 'CPI inflation', unit: '%', placeholder: '0.00' },
    { key: 'sbi_eblr_pct', label: 'SBI EBLR + 2%', unit: '%', placeholder: '0.00' },
    { key: 'bee_energy_audit_fee', label: 'BEE audit fee', unit: '₹L', placeholder: 'Auto', hint: 'Auto-extracted when blank' },
    { key: 'supply_code_sd_rate', label: 'SD interest rate', unit: '%', placeholder: '6.75', hint: 'Default 6.75%' },
    { key: 'norm_loan_opening', label: 'Normative loan opening', unit: '₹L', placeholder: 'Auto' },
    { key: 'sd_balance', label: 'Security deposit balance', unit: '₹L', placeholder: 'Auto' },
    { key: 'cumulative_gap', label: 'Cumulative revenue gap', unit: '₹L', placeholder: 'Auto', hint: 'For carrying cost' },
]

export default function UploadForm({ onSubmit }) {
    const [dragActive, setDragActive] = useState(false)
    const [files, setFiles] = useState(null)
    const [licensee, setLicensee] = useState('')
    const [financialYear, setFinancialYear] = useState('')
    const [params, setParams] = useState(() => Object.fromEntries(PARAMS.map(p => [p.key, ''])))
    const inputRef = useRef(null)

    const handleDrop = (e) => {
        e.preventDefault()
        setDragActive(false)
        if (e.dataTransfer.files?.length) setFiles(e.dataTransfer.files)
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!files || !licensee || !financialYear) return
        const formData = new FormData()
        for (let i = 0; i < files.length; i++) formData.append('files', files[i])
        formData.append('licensee', licensee)
        formData.append('financial_year', financialYear)
        PARAMS.forEach(p => formData.append(p.key, params[p.key]))
        onSubmit(formData)
    }

    const canSubmit = files && licensee && financialYear
    const fileArr = files ? Array.from(files) : []

    return (
        <form onSubmit={handleSubmit} className="hero">
            <section className="hero-left enter-frame">
                <span className="label">KSERC · Truing-up terminal · Regulation 2021</span>
                <h1 className="display hero-title enter-title">
                    Truing-up,<br /><em>reviewed.</em>
                </h1>
                <p className="lede enter-title">
                    Upload a licensee's petition. The engine extracts every cost head, tests it against the MYT norms
                    and Tariff Regulations with deterministic formulas, and drafts the Commission's order for your review.
                </p>
                <div className="hero-meta enter-panel">
                    <div><b>9 stages</b>Extraction → order</div>
                    <div><b>4 licensees</b>SDL · FY 2022–25</div>
                    <div><b>Rs. Lakhs</b>All amounts</div>
                    <div><b>Deterministic</b>Normative math</div>
                    <div><b>Auditable</b>Every decision logged</div>
                    <div><b>Editable</b>Human override</div>
                </div>
            </section>

            <section className="hero-right enter-panel">
                <div className="grid-2">
                    <label className="field">
                        <span className="label">Licensee</span>
                        <select className="select" value={licensee} onChange={e => setLicensee(e.target.value)} required>
                            <option value="" disabled>Select licensee</option>
                            {LICENSEES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                        </select>
                    </label>
                    <label className="field">
                        <span className="label">Financial year</span>
                        <select className="select" value={financialYear} onChange={e => setFinancialYear(e.target.value)} required>
                            <option value="" disabled>Select year</option>
                            {FINANCIAL_YEARS.map(y => <option key={y} value={y}>FY {y}</option>)}
                        </select>
                    </label>
                </div>

                <div
                    className={`dropzone ${dragActive ? 'is-drag' : ''} ${files ? 'has-files' : ''}`}
                    onDragOver={e => { e.preventDefault(); setDragActive(true) }}
                    onDragLeave={() => setDragActive(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    role="button" tabIndex={0}
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
                >
                    <input ref={inputRef} type="file" accept=".pdf" multiple hidden onChange={e => setFiles(e.target.files)} />
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 15V4m0 0L8 8m4-4l4 4M5 15v3a2 2 0 002 2h10a2 2 0 002-2v-3" /></svg>
                    <span className="h3">{files ? `${fileArr.length} petition file${fileArr.length > 1 ? 's' : ''} ready` : 'Drop petition PDFs'}</span>
                    {!files && <span className="hint">Petition, annexures and audited accounts — sent together for cross-reference</span>}
                    {files && (
                        <div className="file-list">
                            {fileArr.map(f => (
                                <div key={f.name}><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span><span>{(f.size / 1024 / 1024).toFixed(1)} MB</span></div>
                            ))}
                        </div>
                    )}
                </div>

                <div>
                    <span className="label" style={{ display: 'block', marginBottom: 10 }}>Parameters · optional</span>
                    <div className="param-grid">
                        {PARAMS.map(p => (
                            <label key={p.key} className="field">
                                <span className="label">{p.label}</span>
                                <span className="affix">
                                    <input type="number" step="0.01" className="input num" placeholder={p.placeholder}
                                        value={params[p.key]} onChange={e => setParams(s => ({ ...s, [p.key]: e.target.value }))} />
                                    <span className="affix-unit">{p.unit}</span>
                                </span>
                                {p.hint && <span className="hint">{p.hint}</span>}
                            </label>
                        ))}
                    </div>
                </div>

                <div style={{ marginTop: 'auto' }}>
                    <Cta type="submit" block disabled={!canSubmit}>Run truing-up audit</Cta>
                </div>
            </section>
        </form>
    )
}
