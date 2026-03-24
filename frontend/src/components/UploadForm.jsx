import { useState } from 'react'
import NeonSelect from './NeonSelect'

const LICENSEES = [
    { value: 'Technopark', label: 'Technopark' },
    { value: 'Infopark', label: 'Infopark' },
    { value: 'CSEZ', label: 'CSEZA / Cezza' },
    { value: 'KDHP', label: 'KDHP' },
]

const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23']

export default function UploadForm({ onSubmit }) {
    const [dragActive, setDragActive] = useState(false)
    const [files, setFiles] = useState(null)
    const [licensee, setLicensee] = useState('')
    const [financialYear, setFinancialYear] = useState('')
    const [inflationPct, setInflationPct] = useState('')
    const [sbiEblrPct, setSbiEblrPct] = useState('')
    const [beeFee, setBeeFee] = useState('')
    const [supplyCodeRate, setSupplyCodeRate] = useState('')
    const [normLoanOpening, setNormLoanOpening] = useState('')
    const [sdBalance, setSdBalance] = useState('')
    const [cumulativeGap, setCumulativeGap] = useState('')

    const handleDrop = (e) => {
        e.preventDefault()
        setDragActive(false)
        const dropped = e.dataTransfer.files
        if (dropped?.length) setFiles(dropped)
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!files || !licensee || !financialYear) return

        const formData = new FormData()
        for (let i = 0; i < files.length; i++) formData.append('files', files[i])
        formData.append('licensee', licensee)
        formData.append('financial_year', financialYear)
        formData.append('inflation_pct', inflationPct)
        formData.append('sbi_eblr_pct', sbiEblrPct)
        formData.append('bee_energy_audit_fee', beeFee)
        formData.append('supply_code_sd_rate', supplyCodeRate)
        formData.append('norm_loan_opening', normLoanOpening)
        formData.append('sd_balance', sdBalance)
        formData.append('cumulative_gap', cumulativeGap)
        onSubmit(formData)
    }

    const canSubmit = files && licensee && financialYear

    return (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Section title */}
            <div>
                <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', letterSpacing: '-0.05em', marginBottom: 6 }}>
                    Submit Petition
                </h2>
                <p className="mono" style={{ lineHeight: 1.8 }}>
                    Upload licensee petition PDFs for automated compliance analysis
                </p>
            </div>

            {/* Row: Licensee + FY */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                    <label className="mono-wide" style={{ display: 'block', marginBottom: 8 }}>Licensee</label>
                    <NeonSelect value={licensee} onChange={setLicensee} options={LICENSEES} placeholder="Select licensee..." />
                </div>
                <div>
                    <label className="mono-wide" style={{ display: 'block', marginBottom: 8 }}>Financial Year</label>
                    <NeonSelect value={financialYear} onChange={setFinancialYear} options={FINANCIAL_YEARS} placeholder="Select year..." />
                </div>
            </div>

            {/* Parameter cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        📈 CPI Inflation
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={inflationPct} placeholder="0.00"
                            onChange={e => setInflationPct(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>%</span>
                    </div>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🏛️ SBI EBLR + 2%
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={sbiEblrPct} placeholder="0.00"
                            onChange={e => setSbiEblrPct(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>%</span>
                    </div>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🔋 BEE Audit Fee
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={beeFee} placeholder="0.00"
                            onChange={e => setBeeFee(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>₹L</span>
                    </div>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 8, fontSize: '9px' }}>Auto-extract</p>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🔐 SD Interest Rate
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={supplyCodeRate} placeholder="6.75"
                            onChange={e => setSupplyCodeRate(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>%</span>
                    </div>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 8, fontSize: '9px' }}>Default 6.75%</p>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🏦 Norm. Loan Opening
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={normLoanOpening} placeholder="Auto"
                            onChange={e => setNormLoanOpening(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>₹L</span>
                    </div>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 8, fontSize: '9px' }}>Normative loan opening balance</p>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🔒 SD Balance
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={sdBalance} placeholder="Auto"
                            onChange={e => setSdBalance(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>₹L</span>
                    </div>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 8, fontSize: '9px' }}>Consumer security deposit balance</p>
                </div>

                <div className="lum-card" style={{ padding: '22px 24px' }}>
                    <p className="mono-wide" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        📊 Cumulative Rev. Gap
                    </p>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                        <input type="number" step="0.01" value={cumulativeGap} placeholder="Auto"
                            onChange={e => setCumulativeGap(e.target.value)}
                            className="neon-input" style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 600, textAlign: 'right', padding: '14px 16px', letterSpacing: '0.02em' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>₹L</span>
                    </div>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 8, fontSize: '9px' }}>For carrying cost calculation</p>
                </div>
            </div>

            {/* Drop Zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragActive(true) }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                onClick={() => document.getElementById('neon-file-input').click()}
                className="lum-card"
                style={{
                    padding: '50px 32px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    borderColor: dragActive ? 'var(--border-accent)' : files ? 'var(--border-accent)' : undefined,
                    background: dragActive ? 'rgba(191, 255, 0, 0.03)' : files ? 'rgba(191, 255, 0, 0.02)' : undefined,
                    transition: 'all 0.3s var(--ease-expo)',
                }}
            >
                <input id="neon-file-input" type="file" accept=".pdf" multiple
                    onChange={e => setFiles(e.target.files)}
                    style={{ display: 'none' }} />
                <div style={{ fontSize: '2rem', marginBottom: 12, opacity: files ? 1 : 0.3 }}>
                    {files ? '✓' : '🗃️'}
                </div>
                <p className="mono-wide" style={{ color: files ? 'var(--accent)' : 'var(--text-secondary)', marginBottom: 6 }}>
                    {files ? `${files.length} file${files.length > 1 ? 's' : ''} selected` : 'Upload Petition PDFs'}
                </p>
                <p className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '9px' }}>
                    {files ? Array.from(files).map(f => f.name).join(', ') : 'Click or drag PDFs here'}
                </p>
            </div>

            {/* Submit */}
            <button type="submit" disabled={!canSubmit} className="laser-btn"
                style={{ width: '100%', padding: '16px 24px', fontSize: '0.85rem' }}>
                🚀 Run Audit Pipeline
            </button>
        </form>
    )
}
