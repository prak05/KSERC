import { useState } from 'react'
import { PageHead } from './ui'
import { fmt } from './format'

/* Historical truing-up outcomes (seeded from KSERC research) and the fixed rules the engine applies. */
const HISTORY = [
    { licensee: 'Technopark', fy: '2020-21', claimed: null, approved: 280.42, outcome: 'SURPLUS', note: 'Highest surplus on record' },
    { licensee: 'CSEZA', fy: '2022-23', claimed: null, approved: 135.14, outcome: 'SURPLUS', note: '' },
    { licensee: 'KDHPCL', fy: '2022-23', claimed: null, approved: 116.91, outcome: 'SURPLUS', note: '' },
    { licensee: 'CSEZA', fy: '2023-24', claimed: -3.42, approved: 87.85, outcome: 'REVERSAL', note: 'Claimed a deficit; the Commission found a surplus' },
    { licensee: 'KDHPCL', fy: '2021-22', claimed: 13.61, approved: 58.72, outcome: 'OVERSHOOT', note: 'Approved four times the amount claimed' },
    { licensee: 'Infopark', fy: '2020-21', claimed: -76.53, approved: -60.80, outcome: 'GAP', note: '15.73 L disallowed' },
    { licensee: 'Infopark', fy: '2024-25', claimed: -79.76, approved: -64.72, outcome: 'GAP', note: '15.04 L disallowed' },
]

const OUTCOME = { SURPLUS: 'pill-ok', GAP: 'pill-bad', REVERSAL: 'pill-warn', OVERSHOOT: 'pill-accent' }

const REJECTIONS = [
    ['Section 3(1) electricity duty', 'Cannot be passed through to consumers'],
    ['CSR expenses', 'An appropriation of profit, not a distribution cost'],
    ['RPO liability provisions', 'Only actual REC payments are allowed'],
]

const signedFmt = (v) => (v === null ? '—' : (v > 0 ? '+' : '') + fmt(v))

export default function Benchmarks() {
    const [tab, setTab] = useState('history')

    return (
        <section className="stack view">
            <PageHead eyebrow="Reference · Benchmarks" title="Precedent & rules"
                lede="Past Commission outcomes used to sanity-check the engine, and the rules it applies without exception." />

            <div className="stats enter-panel">
                <div className="stat"><span className="label">Highest surplus</span><div className="stat-value ok">280.42</div><div className="stat-unit">Technopark · FY 2020-21</div></div>
                <div className="stat"><span className="label">Largest approved gap</span><div className="stat-value bad">64.72</div><div className="stat-unit">Infopark · FY 2024-25</div></div>
                <div className="stat"><span className="label">Notable reversal</span><div className="stat-value warn">87.85</div><div className="stat-unit">CSEZA · FY 2023-24</div></div>
                <div className="stat"><span className="label">Cases on record</span><div className="stat-value">{HISTORY.length}</div><div className="stat-unit">SDL licensees</div></div>
            </div>

            <div className="tabs">
                <button className={`tab ${tab === 'history' ? 'is-active' : ''}`} onClick={() => setTab('history')}><span className="num">01</span>Historical orders</button>
                <button className={`tab ${tab === 'rules' ? 'is-active' : ''}`} onClick={() => setTab('rules')}><span className="num">02</span>Fixed rules</button>
            </div>

            {tab === 'history' ? (
                <div className="card table-wrap view" key="history">
                    <table className="table">
                        <thead><tr><th style={{ width: 48 }}>#</th><th>Licensee</th><th>Financial year</th><th className="r">Claimed</th><th className="r">Approved</th><th>Outcome</th><th>Note</th></tr></thead>
                        <tbody>
                            {HISTORY.map((h, i) => (
                                <tr key={`${h.licensee}-${h.fy}`}>
                                    <td className="idx">{String(i + 1).padStart(2, '0')}</td>
                                    <td style={{ fontWeight: 500 }}>{h.licensee}</td>
                                    <td className="num">FY {h.fy}</td>
                                    <td className="r num muted">{signedFmt(h.claimed)}</td>
                                    <td className={`r num ${h.approved > 0 ? 'ok' : 'bad'}`} style={{ fontWeight: 600 }}>{signedFmt(h.approved)}</td>
                                    <td><span className={`pill ${OUTCOME[h.outcome]}`}>{h.outcome.toLowerCase()}</span></td>
                                    <td className="muted">{h.note}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="grid-2 view" key="rules">
                    <div className="card">
                        <div className="card-head"><span className="h3">Always disallowed</span><span className="spacer" /><span className="label">Approved ₹0</span></div>
                        <div className="table-wrap"><table className="table"><tbody>
                            {REJECTIONS.map(([item, basis]) => <tr key={item}><td style={{ fontWeight: 500 }}>{item}</td><td className="muted">{basis}</td></tr>)}
                        </tbody></table></div>
                    </div>
                    <div className="card card-pad stack" style={{ gap: 12 }}>
                        <p className="h3">O&amp;M normative cap</p>
                        <span className="label">Tariff Regulations 2021 · Reg. 12(3)</span>
                        <div className="formula">Normative cap = Previous approved × (1 + escalation)</div>
                        <p className="muted">Actual spend above the cap is disallowed. Documented one-time expenditure — terminal-benefit arrears, emergency repairs — may be allowed over the cap once verified.</p>
                        <p className="muted">Items above ₹5 L claimed as R&amp;M that qualify as capital are reclassified; only depreciation at the approved rate is allowed.</p>
                    </div>
                    <div className="card card-pad stack" style={{ gap: 12, gridColumn: '1 / -1' }}>
                        <p className="h3">Distribution-loss efficiency sharing</p>
                        <div className="grid-2">
                            <div className="formula">Efficiency gain (MU) = (Target % − Actual %) × Energy input ÷ 100</div>
                            <div className="formula">Savings = Efficiency gain × Power-purchase cost per unit</div>
                        </div>
                        <p className="muted">When actual loss is below the KSERC target the licensee retains two-thirds of the resulting power-purchase savings. Infopark FY 2024-25: target 4.23%, actual 2.86%.</p>
                    </div>
                </div>
            )}
        </section>
    )
}
