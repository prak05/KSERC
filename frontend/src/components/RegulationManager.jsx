import { useCallback, useEffect, useRef, useState } from 'react'
import { Notice, PageHead } from './ui'

const CATEGORIES = [
    { id: 'regulations', label: 'Regulations', desc: 'Tariff Regulations and amendments' },
    { id: 'myt_orders', label: 'MYT orders', desc: 'Multi-year tariff orders' },
    { id: 'past_orders', label: 'Past orders', desc: 'Previous truing-up orders' },
    { id: 'other_licensee_orders', label: 'Other licensees', desc: 'Orders for other SDL licensees' },
]

const METHOD = { pymupdf: 'Text layer', 'model-ocr': 'Model OCR', llm: 'Model OCR' }

function formatChars(n = 0) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
    return `${n}`
}

export default function RegulationManager() {
    const [docs, setDocs] = useState([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [uploadProgress, setUploadProgress] = useState('')
    const [selectedCategory, setSelectedCategory] = useState('regulations')
    const [selectedFile, setSelectedFile] = useState(null)
    const [error, setError] = useState(null)
    const [deleteConfirm, setDeleteConfirm] = useState(null)
    const fileRef = useRef(null)

    const fetchDocs = useCallback(async () => {
        try {
            setLoading(true)
            const resp = await fetch('/api/regulations')
            if (!resp.ok) throw new Error('Could not load the regulation store')
            const data = await resp.json()
            setDocs(data.docs || [])
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchDocs() }, [fetchDocs])

    const handleUpload = async () => {
        if (!selectedFile) return
        setUploading(true); setUploadProgress('Extracting text from PDF…'); setError(null)
        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('category', selectedCategory)
        try {
            const resp = await fetch('/api/regulations/upload', { method: 'POST', body: formData })
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}))
                throw new Error(err.detail || `Upload failed (${resp.status})`)
            }
            const result = await resp.json()
            setUploadProgress(`Stored ${formatChars(result.chars)} characters via ${METHOD[result.method] || result.method}`)
            setSelectedFile(null)
            if (fileRef.current) fileRef.current.value = ''
            await fetchDocs()
            setTimeout(() => setUploadProgress(''), 3000)
        } catch (e) {
            setError(e.message); setUploadProgress('')
        } finally {
            setUploading(false)
        }
    }

    const handleDelete = async (docId) => {
        try {
            const resp = await fetch(`/api/regulations/${docId}`, { method: 'DELETE' })
            if (!resp.ok) throw new Error('Delete failed')
            setDeleteConfirm(null)
            await fetchDocs()
        } catch (e) {
            setError(e.message)
        }
    }

    const grouped = {}
    docs.forEach(d => { (grouped[d.category || 'other'] ||= []).push(d) })
    const total = docs.reduce((s, d) => s + (d.chars || 0), 0)

    return (
        <section className="stack view">
            <PageHead eyebrow="Reference · Regulation store" title="Regulatory corpus"
                lede="Regulations and orders are extracted to text once. The analyst and the audit agents retrieve the relevant clauses from here instead of re-reading PDFs.">
                <span className="pill pill-plain num">{docs.length} documents</span>
                <span className="pill pill-plain num">{formatChars(total)} characters</span>
            </PageHead>

            <div className="card enter-panel">
                <div className="card-head"><span className="h3">Add a document</span></div>
                <div className="card-body row" style={{ alignItems: 'flex-end' }}>
                    <label className="field" style={{ width: 280 }}>
                        <span className="label">Category</span>
                        <select className="select" value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)}>
                            {CATEGORIES.map(c => <option key={c.id} value={c.id} title={c.desc}>{c.label}</option>)}
                        </select>
                    </label>
                    <label className="field" style={{ flex: 1, minWidth: 220 }}>
                        <span className="label">PDF</span>
                        <input ref={fileRef} type="file" accept=".pdf" hidden onChange={e => setSelectedFile(e.target.files?.[0] || null)} />
                        <button type="button" className="btn" style={{ justifyContent: 'flex-start' }} onClick={() => fileRef.current?.click()}>
                            {selectedFile ? selectedFile.name : 'Choose file…'}
                        </button>
                    </label>
                    <button className="btn btn-accent" disabled={!selectedFile || uploading} onClick={handleUpload}>
                        {uploading ? 'Extracting…' : 'Extract & store'}
                    </button>
                </div>
                <div className="card-body hint" style={{ borderTop: '1px solid var(--line)' }}>
                    Text-layer PDFs are read directly. Scanned PDFs fall back to model OCR.
                </div>
            </div>

            {uploadProgress && <Notice tone={uploading ? 'info' : 'ok'}>{uploadProgress}</Notice>}
            {error && <Notice tone="bad" onClose={() => setError(null)}>{error}</Notice>}

            {loading ? (
                <div className="card"><div className="progress is-indeterminate"><span /></div><div className="empty">Loading the regulation store…</div></div>
            ) : docs.length === 0 ? (
                <div className="card empty"><p className="h3">The store is empty</p><p>Add a regulation above. Reference PDFs in the documents folder are also extracted on first use.</p></div>
            ) : (
                Object.entries(grouped).map(([cat, catDocs]) => {
                    const info = CATEGORIES.find(c => c.id === cat) || { label: cat }
                    return (
                        <div key={cat} className="card">
                            <div className="card-head"><span className="h3">{info.label}</span><span className="faint num">{catDocs.length}</span></div>
                            <div className="table-wrap">
                                <table className="table">
                                    <tbody>
                                        {catDocs.map(doc => (
                                            <tr key={doc.doc_id}>
                                                <td style={{ fontWeight: 500 }}>{doc.filename}</td>
                                                <td className="num faint" style={{ width: 170 }}>{doc.extracted_at?.replace('T', ' ') || '—'}</td>
                                                <td style={{ width: 120 }}><span className="pill pill-plain">{METHOD[doc.method] || 'Unknown'}</span></td>
                                                <td className="r num muted" style={{ width: 80 }}>{formatChars(doc.chars)}</td>
                                                <td className="r" style={{ width: 170 }}>
                                                    {deleteConfirm === doc.doc_id ? (
                                                        <span className="row" style={{ justifyContent: 'flex-end' }}>
                                                            <button className="btn btn-sm btn-danger" onClick={() => handleDelete(doc.doc_id)}>Confirm delete</button>
                                                            <button className="btn btn-sm btn-ghost" onClick={() => setDeleteConfirm(null)}>Cancel</button>
                                                        </span>
                                                    ) : (
                                                        <button className="btn btn-sm btn-ghost btn-danger" onClick={() => setDeleteConfirm(doc.doc_id)}>Delete</button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )
                })
            )}
        </section>
    )
}
