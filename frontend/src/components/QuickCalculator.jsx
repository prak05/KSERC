import { useState } from 'react'
import { PageHead } from './ui'
import { fmt } from './format'

const n = (v) => (v === '' || v === null || Number.isNaN(Number(v)) ? 0 : Number(v))

function NumField({ label, unit, value, onChange }) {
    return (
        <label className="field">
            <span className="label">{label}</span>
            <span className="affix">
                <input type="number" step="any" className="input num" value={value} placeholder="0.00" onChange={e => onChange(e.target.value)} />
                <span className="affix-unit">{unit}</span>
            </span>
        </label>
    )
}

function Panel({ title, formula, children, result, resultLabel, tone }) {
    return (
        <div className="card card-pad stack" style={{ gap: 14 }}>
            <p className="h3">{title}</p>
            <div className="formula">{formula}</div>
            {children}
            <div className="result-line">
                <span className="label">{resultLabel}</span>
                <span className={`num ${tone || ''}`}>{result}</span>
            </div>
        </div>
    )
}

export default function QuickCalculator() {
    const [arr, setArr] = useState('')
    const [rev, setRev] = useState('')
    const [base, setBase] = useState('')
    const [cpi, setCpi] = useState('')
    const [wpi, setWpi] = useState('')
    const [equity, setEquity] = useState('')
    const [roe, setRoe] = useState('14')

    const gap = n(arr) - n(rev)
    const escalation = 0.7 * n(cpi) / 100 + 0.3 * n(wpi) / 100
    const om = n(base) * (1 + escalation)
    const returnOnEquity = n(equity) * n(roe) / 100

    return (
        <section className="stack view">
            <PageHead eyebrow="Tools · Deterministic, no model involved" title="Quick calculator"
                lede="The same normative formulas the audit engine applies, for checking a figure during a hearing. All amounts in Rs. Lakhs." />
            <div className="grid-3 enter-panel">
                <Panel title="Revenue gap / surplus" formula="Gap = ARR − Approved revenue"
                    resultLabel={gap > 0 ? 'Revenue gap' : 'Revenue surplus'} result={fmt(Math.abs(gap))} tone={gap > 0 ? 'bad' : gap < 0 ? 'ok' : ''}>
                    <NumField label="Aggregate revenue requirement" unit="₹L" value={arr} onChange={setArr} />
                    <NumField label="Approved revenue" unit="₹L" value={rev} onChange={setRev} />
                </Panel>
                <Panel title="O&M escalation" formula="O&M = Base × (1 + 0.7·CPI + 0.3·WPI)"
                    resultLabel={`Escalated O&M · ${(escalation * 100).toFixed(2)}%`} result={fmt(om)}>
                    <NumField label="Base-year O&M" unit="₹L" value={base} onChange={setBase} />
                    <div className="grid-2">
                        <NumField label="CPI" unit="%" value={cpi} onChange={setCpi} />
                        <NumField label="WPI" unit="%" value={wpi} onChange={setWpi} />
                    </div>
                </Panel>
                <Panel title="Return on equity" formula="RoE = Equity × rate" resultLabel="Allowable return" result={fmt(returnOnEquity)}>
                    <NumField label="Normative equity" unit="₹L" value={equity} onChange={setEquity} />
                    <NumField label="Rate" unit="%" value={roe} onChange={setRoe} />
                </Panel>
            </div>
        </section>
    )
}
