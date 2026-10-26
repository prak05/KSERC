import { useEffect, useRef, useState } from 'react'
import { PageHead } from './ui'

const SUGGESTIONS = [
    'How is the O&M normative cap escalated under the 2021 Regulations?',
    'What return on equity is allowed for SDL licensees?',
    'How was distribution loss efficiency gain shared for Infopark in FY 2022-23?',
    'Which expenses are disallowed in every truing-up order?',
]

export default function Analyst() {
    const [messages, setMessages] = useState([])
    const [question, setQuestion] = useState('')
    const [busy, setBusy] = useState(false)
    const logRef = useRef(null)

    useEffect(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
    }, [messages.length, busy])

    const ask = async (q) => {
        const text = (q ?? question).trim()
        if (!text || busy) return
        setQuestion('')
        setMessages(m => [...m, { role: 'user', text }])
        setBusy(true)
        try {
            const resp = await fetch('/api/ask', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text }),
            })
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}))
                throw new Error(err.detail || `The analyst is unavailable (${resp.status})`)
            }
            const data = await resp.json()
            setMessages(m => [...m, { role: 'model', text: data.answer || 'No answer returned.', sources: data.sources || [] }])
        } catch (e) {
            setMessages(m => [...m, { role: 'model', text: e.message, error: true }])
        } finally {
            setBusy(false)
        }
    }

    return (
        <section className="stack view">
            <PageHead eyebrow="Analyst · Retrieval over the regulatory corpus" title="Ask the regulations"
                lede="Answers are grounded in the stored Tariff Regulations, MYT orders and past truing-up orders, with the passages they came from." />

            <div className="card chat enter-panel">
                <div className="chat-log" ref={logRef}>
                    {messages.length === 0 && (
                        <div className="stack" style={{ gap: 12 }}>
                            <span className="label">Try</span>
                            <div className="suggestions">
                                {SUGGESTIONS.map(s => <button key={s} className="btn" onClick={() => ask(s)}>{s}</button>)}
                            </div>
                        </div>
                    )}
                    {messages.map((m, i) => (
                        <div key={i} className={`msg ${m.role === 'user' ? 'is-user' : 'is-model'}`}>
                            <span className="who">{m.role === 'user' ? 'You' : 'Analyst'}</span>
                            <div>
                                <div className={`body ${m.error ? 'bad' : ''}`}>{m.text}</div>
                                {m.sources?.length > 0 && (
                                    <div className="sources">{m.sources.map(s => <span key={s}>{s}</span>)}</div>
                                )}
                            </div>
                        </div>
                    ))}
                    {busy && (
                        <div className="msg is-model">
                            <span className="who">Analyst</span>
                            <div className="body faint">Retrieving clauses and drafting an answer…</div>
                        </div>
                    )}
                </div>
                {busy && <div className="progress is-indeterminate"><span /></div>}
                <form className="composer" onSubmit={e => { e.preventDefault(); ask() }}>
                    <textarea className="textarea" rows={1} placeholder="Ask about a clause, a norm or a past order…" value={question}
                        onChange={e => setQuestion(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() } }} />
                    <button className="btn btn-accent" style={{ height: 40 }} disabled={busy || !question.trim()}>Ask</button>
                </form>
            </div>
        </section>
    )
}
