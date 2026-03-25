import { useState, useEffect, useCallback } from 'react'

const CATEGORIES = [
    { id: 'regulations', label: 'Regulations', desc: 'KSERC Tariff Regulations, Amendments' },
    { id: 'myt_orders', label: 'MYT Orders', desc: 'Multi-Year Tariff Orders' },
    { id: 'past_orders', label: 'Past Orders', desc: 'Previous Truing-Up Orders' },
    { id: 'other_licensee_orders', label: 'Other Licensee Orders', desc: 'Orders for other SDL licensees' },
]

const METHOD_BADGES = {
    pymupdf: { label: 'PyMuPDF', color: '#00d4ff', bg: 'rgba(0,212,255,0.1)' },
    gemini: { label: 'Gemini AI', color: '#a855f7', bg: 'rgba(168,85,247,0.1)' },
    unknown: { label: 'Unknown', color: '#888', bg: 'rgba(136,136,136,0.1)' },
}

function formatChars(n) {
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

    const fetchDocs = useCallback(async () => {
        try {
            setLoading(true)
            const resp = await fetch('/api/regulations')
            if (!resp.ok) throw new Error('Failed to fetch')
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
        setUploading(true)
        setUploadProgress('Extracting text from PDF…')
        setError(null)

        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('category', selectedCategory)

        try {
            const resp = await fetch('/api/regulations/upload', {
                method: 'POST',
                body: formData,
            })
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}))
                throw new Error(err.detail || `Upload failed (${resp.status})`)
            }
            const result = await resp.json()
            setUploadProgress(`✅ Extracted ${formatChars(result.chars)} chars via ${result.method}`)
            setSelectedFile(null)
            // Reset file input
            const fileInput = document.getElementById('reg-file-input')
            if (fileInput) fileInput.value = ''
            await fetchDocs()
            setTimeout(() => setUploadProgress(''), 3000)
        } catch (e) {
            setError(e.message)
            setUploadProgress('')
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

    // Group docs by category
    const grouped = {}
    docs.forEach(d => {
        const cat = d.category || 'other'
        if (!grouped[cat]) grouped[cat] = []
        grouped[cat].push(d)
    })

    return (
        <div className="animate-slide-up">
            {/* Header */}
            <div className="glass-card" style={{ padding: '28px 32px', marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                    <div>
                        <h2 style={{ fontSize: '1.3rem', letterSpacing: '-0.03em', marginBottom: 6 }}>
                            ⚖️ Regulation Document Store
                        </h2>
                        <p className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            Pre-extracted regulation text stored in Firestore. Used by the audit pipeline for fast regulation queries — no PDF scanning needed.
                        </p>
                    </div>
                    <div className="mono" style={{
                        padding: '8px 16px', borderRadius: 8,
                        background: 'rgba(0, 255, 136, 0.06)', border: '1px solid rgba(0, 255, 136, 0.2)',
                        fontSize: '0.8rem', color: 'var(--green)', whiteSpace: 'nowrap',
                    }}>
                        {docs.length} documents • {formatChars(docs.reduce((s, d) => s + (d.chars || 0), 0))} chars total
                    </div>
                </div>
            </div>

            {/* Upload Section */}
            <div className="glass-card" style={{ padding: '24px 28px', marginBottom: 24, border: '1px solid rgba(0, 212, 255, 0.15)' }}>
                <h3 style={{ fontSize: '0.95rem', letterSpacing: '-0.02em', marginBottom: 16, color: '#00d4ff' }}>
                    📤 Upload New Regulation
                </h3>

                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                    {/* Category Selector */}
                    <div style={{ flex: '0 0 220px' }}>
                        <label className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>
                            CATEGORY
                        </label>
                        <select
                            value={selectedCategory}
                            onChange={e => setSelectedCategory(e.target.value)}
                            style={{
                                width: '100%', padding: '10px 12px', borderRadius: 8,
                                background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
                                color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
                                outline: 'none', cursor: 'pointer',
                            }}
                        >
                            {CATEGORIES.map(c => (
                                <option key={c.id} value={c.id} style={{ background: '#1a1a2e' }}>
                                    {c.label} — {c.desc}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* File Input */}
                    <div style={{ flex: 1, minWidth: 200 }}>
                        <label className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>
                            PDF FILE
                        </label>
                        <input
                            id="reg-file-input"
                            type="file"
                            accept=".pdf"
                            onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                            style={{
                                width: '100%', padding: '8px 12px', borderRadius: 8,
                                background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)',
                                color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
                            }}
                        />
                    </div>

                    {/* Upload Button */}
                    <button
                        className="laser-btn"
                        onClick={handleUpload}
                        disabled={!selectedFile || uploading}
                        style={{
                            padding: '10px 24px', fontSize: '0.85rem', whiteSpace: 'nowrap',
                            opacity: (!selectedFile || uploading) ? 0.5 : 1,
                        }}
                    >
                        {uploading ? '⏳ Extracting…' : '📥 Extract & Store'}
                    </button>
                </div>

                {/* Upload status */}
                {uploadProgress && (
                    <div className="mono" style={{
                        marginTop: 12, padding: '8px 14px', borderRadius: 6,
                        background: uploadProgress.startsWith('✅') ? 'rgba(0,255,136,0.08)' : 'rgba(0,212,255,0.08)',
                        border: `1px solid ${uploadProgress.startsWith('✅') ? 'rgba(0,255,136,0.2)' : 'rgba(0,212,255,0.2)'}`,
                        fontSize: '0.8rem',
                        color: uploadProgress.startsWith('✅') ? 'var(--green)' : '#00d4ff',
                    }}>
                        {uploadProgress}
                    </div>
                )}

                <p className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: 10 }}>
                    Extraction uses <strong style={{ color: '#00d4ff' }}>PyMuPDF</strong> (fast, for structured text PDFs).
                    Falls back to <strong style={{ color: '#a855f7' }}>Gemini AI</strong> for scanned/image PDFs.
                </p>
            </div>

            {/* Error */}
            {error && (
                <div className="glass-card" style={{ padding: '12px 20px', marginBottom: 16, borderColor: 'rgba(255,68,68,0.3)' }}>
                    <p className="mono" style={{ color: 'var(--red)', fontSize: '0.85rem' }}>
                        🔴 {error}
                        <button onClick={() => setError(null)} style={{
                            marginLeft: 12, background: 'none', border: 'none', color: 'var(--text-tertiary)',
                            cursor: 'pointer', fontSize: '0.85rem',
                        }}>✕</button>
                    </p>
                </div>
            )}

            {/* Document List */}
            {loading ? (
                <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
                    <div className="mono" style={{ color: 'var(--text-secondary)' }}>Loading regulations…</div>
                </div>
            ) : docs.length === 0 ? (
                <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', marginBottom: 12 }}>📭</div>
                    <div className="mono" style={{ color: 'var(--text-secondary)' }}>No regulation documents stored yet. Upload one above.</div>
                </div>
            ) : (
                Object.entries(grouped).map(([cat, catDocs]) => {
                    const catInfo = CATEGORIES.find(c => c.id === cat) || { label: cat, desc: '' }
                    return (
                        <div key={cat} style={{ marginBottom: 20 }}>
                            <div className="mono" style={{
                                fontSize: '0.7rem', letterSpacing: '0.15em', textTransform: 'uppercase',
                                color: 'var(--text-tertiary)', marginBottom: 8, paddingLeft: 4,
                            }}>
                                {catInfo.label} ({catDocs.length})
                            </div>
                            <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                                {catDocs.map((doc, i) => {
                                    const badge = METHOD_BADGES[doc.method] || METHOD_BADGES.unknown
                                    return (
                                        <div
                                            key={doc.doc_id}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 12,
                                                padding: '14px 20px',
                                                borderBottom: i < catDocs.length - 1 ? '1px solid var(--border)' : 'none',
                                                transition: 'background 0.15s',
                                            }}
                                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            {/* Icon */}
                                            <div style={{ fontSize: '1.2rem', opacity: 0.6 }}>📄</div>

                                            {/* Filename */}
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{
                                                    fontSize: '0.85rem', color: '#fff', fontWeight: 500,
                                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                                }}>
                                                    {doc.filename}
                                                </div>
                                                <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: 2 }}>
                                                    {doc.extracted_at?.replace('T', ' ') || '—'}
                                                </div>
                                            </div>

                                            {/* Method badge */}
                                            <span className="mono" style={{
                                                fontSize: '0.65rem', padding: '3px 8px', borderRadius: 4,
                                                background: badge.bg, color: badge.color,
                                                border: `1px solid ${badge.color}33`,
                                                letterSpacing: '0.05em',
                                            }}>
                                                {badge.label}
                                            </span>

                                            {/* Chars */}
                                            <div className="mono" style={{
                                                fontSize: '0.8rem', color: 'var(--text-secondary)',
                                                minWidth: 60, textAlign: 'right',
                                            }}>
                                                {formatChars(doc.chars)}
                                            </div>

                                            {/* Delete */}
                                            {deleteConfirm === doc.doc_id ? (
                                                <div style={{ display: 'flex', gap: 6 }}>
                                                    <button
                                                        onClick={() => handleDelete(doc.doc_id)}
                                                        style={{
                                                            background: 'rgba(255,68,68,0.15)', border: '1px solid rgba(255,68,68,0.3)',
                                                            color: '#ff4444', borderRadius: 4, padding: '4px 10px',
                                                            cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.7rem',
                                                        }}
                                                    >
                                                        Confirm
                                                    </button>
                                                    <button
                                                        onClick={() => setDeleteConfirm(null)}
                                                        style={{
                                                            background: 'transparent', border: '1px solid var(--border)',
                                                            color: 'var(--text-tertiary)', borderRadius: 4, padding: '4px 10px',
                                                            cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.7rem',
                                                        }}
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    onClick={() => setDeleteConfirm(doc.doc_id)}
                                                    title="Delete"
                                                    style={{
                                                        background: 'transparent', border: 'none',
                                                        color: 'var(--text-tertiary)', cursor: 'pointer',
                                                        fontSize: '1rem', padding: '4px 8px', borderRadius: 4,
                                                        transition: 'all 0.15s',
                                                    }}
                                                    onMouseEnter={e => { e.currentTarget.style.color = '#ff4444'; e.currentTarget.style.background = 'rgba(255,68,68,0.1)' }}
                                                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-tertiary)'; e.currentTarget.style.background = 'transparent' }}
                                                >
                                                    🗑
                                                </button>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )
                })
            )}
        </div>
    )
}
