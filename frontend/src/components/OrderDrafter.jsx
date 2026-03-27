import { useState, useCallback, useRef, useEffect } from 'react'

/**
 * OrderDrafter — Full-page preview editor with inline editing.
 * 
 * The preview HTML is shown in an iframe. When edit mode is on,
 * all paragraphs and table cells become contenteditable directly
 * in the preview. Finalize reads the edited HTML back and generates the PDF.
 * 
 * Props:
 *   analysisId: string
 *   analysisData: object
 *   onBack: () => void
 */
export default function OrderDrafter({ analysisId, analysisData, onBack }) {
    const [previewHtml, setPreviewHtml] = useState(null)
    const [pdfUrl, setPdfUrl] = useState(null)
    const [loading, setLoading] = useState(false)
    const [editMode, setEditMode] = useState(false)
    const [status, setStatus] = useState(null)
    const [hasEdits, setHasEdits] = useState(false)
    const iframeRef = useRef(null)

    // ── Inject edit-mode CSS + JS into preview HTML ─────────────────
    const makeEditable = useCallback((html) => {
        if (!html) return html
        // Inject a script that makes all p, td, th, li, h1-h6, span contenteditable
        const editScript = `
<style>
  [contenteditable="true"] { outline: 2px dashed rgba(0,120,255,0.25); outline-offset: 2px; }
  [contenteditable="true"]:focus { outline: 2px solid rgba(0,120,255,0.6); background: rgba(0,120,255,0.04); }
  td[contenteditable="true"], th[contenteditable="true"] { 
    outline: 1px dashed rgba(0,120,255,0.2); outline-offset: 0; min-width: 30px;
  }
  td[contenteditable="true"]:focus, th[contenteditable="true"]:focus { 
    outline: 2px solid rgba(0,120,255,0.6); background: rgba(230,240,255,0.3); 
  }
  .edit-banner {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: linear-gradient(135deg, #1a5aff, #0040dd); color: #fff;
    padding: 6px 16px; font-size: 12px; font-family: system-ui, sans-serif;
    display: flex; align-items: center; gap: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .edit-banner::before { content: "✏️"; }
  body { padding-top: 32px !important; }
</style>
<div class="edit-banner">EDIT MODE — Click any text or table cell to edit directly</div>
<script>
  document.querySelectorAll('p, td, th, li, h1, h2, h3, h4, h5, h6').forEach(el => {
    el.contentEditable = 'true';
  });
  document.body.addEventListener('input', () => {
    window.parent.postMessage({ type: 'PREVIEW_EDITED' }, '*');
  });
</script>`
        // Inject before </body>
        if (html.includes('</body>')) {
            return html.replace('</body>', editScript + '</body>')
        }
        return html + editScript
    }, [])

    const makeReadOnly = useCallback((html) => {
        if (!html) return html
        // Strip any previously injected edit script/styles
        return html
            .replace(/<style>[\s\S]*?\.edit-banner[\s\S]*?<\/style>/g, '')
            .replace(/<div class="edit-banner">[\s\S]*?<\/div>/g, '')
            .replace(/<script>[\s\S]*?contentEditable[\s\S]*?<\/script>/g, '')
    }, [])

    // ── Listen for edit events from iframe ───────────────────────────
    useEffect(() => {
        const handler = (e) => {
            if (e.data?.type === 'PREVIEW_EDITED') {
                setHasEdits(true)
            }
        }
        window.addEventListener('message', handler)
        return () => window.removeEventListener('message', handler)
    }, [])

    // ── Toggle edit mode on the iframe ───────────────────────────────
    const toggleEditMode = useCallback(() => {
        const nextEdit = !editMode
        setEditMode(nextEdit)

        if (iframeRef.current?.contentDocument) {
            const doc = iframeRef.current.contentDocument

            if (nextEdit) {
                // Enable editing
                doc.querySelectorAll('p, td, th, li, h1, h2, h3, h4, h5, h6').forEach(el => {
                    el.contentEditable = 'true'
                })
                // Add banner
                if (!doc.querySelector('.edit-banner')) {
                    const style = doc.createElement('style')
                    style.setAttribute('data-edit', 'true')
                    style.textContent = `
                        [contenteditable="true"] { outline: 2px dashed rgba(0,120,255,0.25); outline-offset: 2px; cursor: text; }
                        [contenteditable="true"]:focus { outline: 2px solid rgba(0,120,255,0.6); background: rgba(0,120,255,0.04); }
                        td[contenteditable="true"], th[contenteditable="true"] { outline: 1px dashed rgba(0,120,255,0.2); outline-offset: 0; min-width: 30px; }
                        td[contenteditable="true"]:focus, th[contenteditable="true"]:focus { outline: 2px solid rgba(0,120,255,0.6); background: rgba(230,240,255,0.3); }
                        .edit-banner { position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: linear-gradient(135deg, #1a5aff, #0040dd); color: #fff; padding: 6px 16px; font-size: 12px; font-family: system-ui, sans-serif; display: flex; align-items: center; gap: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
                        .edit-banner::before { content: "✏️"; }
                        body { padding-top: 32px !important; }
                    `
                    doc.head.appendChild(style)

                    const banner = doc.createElement('div')
                    banner.className = 'edit-banner'
                    banner.textContent = 'EDIT MODE — Click any text or table cell to edit directly'
                    doc.body.prepend(banner)
                }
                // Track edits
                doc.body.addEventListener('input', () => {
                    setHasEdits(true)
                })
            } else {
                // Disable editing
                doc.querySelectorAll('[contenteditable="true"]').forEach(el => {
                    el.contentEditable = 'false'
                })
                // Remove banner and styles
                doc.querySelector('.edit-banner')?.remove()
                doc.querySelector('style[data-edit]')?.remove()
            }
        }
    }, [editMode])

    // ── Get current HTML from iframe (after edits) ───────────────────
    const getCurrentHtml = useCallback(() => {
        if (!iframeRef.current?.contentDocument) return previewHtml
        const doc = iframeRef.current.contentDocument
        // Clean up edit artifacts before extracting
        const clone = doc.documentElement.cloneNode(true)
        clone.querySelectorAll('.edit-banner').forEach(el => el.remove())
        clone.querySelectorAll('style[data-edit]').forEach(el => el.remove())
        clone.querySelectorAll('[contenteditable]').forEach(el => {
            el.removeAttribute('contenteditable')
        })
        // Remove padding-top override
        const body = clone.querySelector('body')
        if (body) body.style.paddingTop = ''
        return '<!DOCTYPE html><html>' + clone.innerHTML + '</html>'
    }, [previewHtml])

    // ── Generate draft (Gemini only) ─────────────────────────────────
    const handleGenerate = useCallback(async () => {
        setLoading(true)
        setStatus('⏳ Generating Gemini order draft… This may take 2-3 minutes.')
        setPdfUrl(null)
        setPreviewHtml(null)
        setHasEdits(false)
        try {
            const resp = await fetch('/api/generate-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ analysis_id: analysisId }),
            })
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `Server error ${resp.status}`)
            }
            const data = await resp.json()
            setPdfUrl(data.pdf_url)
            if (data.html) {
                setPreviewHtml(data.html)
            }
            setStatus('✅ Gemini order ready — PDF generated! Edit preview or Download.')
        } catch (e) {
            setStatus(`Error: ${e.message}`)
        } finally {
            setLoading(false)
        }
    }, [analysisId])

    // ── Finalize PDF from current (possibly edited) HTML ────────────
    const handleFinalize = useCallback(async () => {
        setLoading(true)
        setStatus('Generating PDF from edited preview…')
        try {
            const html = getCurrentHtml()
            const resp = await fetch('/api/finalize-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ analysis_id: analysisId, html }),
            })
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `PDF generation failed: ${resp.status}`)
            }
            const data = await resp.json()
            setPdfUrl(data.pdf_url)
            setHasEdits(false)
            setStatus('✅ PDF finalized with your edits! Click Download to save.')
        } catch (e) {
            setStatus(`Error: ${e.message}`)
        } finally {
            setLoading(false)
        }
    }, [analysisId, getCurrentHtml])

    // No blob URL needed — we use srcdoc directly

    const licensee = analysisData?.licensee_name || ''
    const fy = analysisData?.financial_year || ''

    return (
        <section className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Header */}
            <div style={{
                display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between',
                alignItems: 'center', gap: 12,
                borderBottom: '1px solid var(--border)', paddingBottom: 16,
            }}>
                <div>
                    <h2 style={{ fontSize: 'clamp(1.2rem, 2.5vw, 1.6rem)', letterSpacing: '-0.04em', marginBottom: 6 }}>
                        📄 Order Drafter
                    </h2>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {licensee && <span className="tag-neutral">{licensee}</span>}
                        {fy && <span className="tag-neutral">FY {fy}</span>}
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <button onClick={onBack} className="btn-secondary">← Back</button>
                    {!previewHtml && !loading && (
                        <button
                            onClick={handleGenerate}
                            disabled={loading}
                            className="btn-primary"
                            style={{ padding: '10px 24px' }}
                        >
                            ⚡ Generate Draft
                        </button>
                    )}
                    {previewHtml && (
                        <>
                            {!loading && (
                                <button
                                    onClick={handleGenerate}
                                    disabled={loading}
                                    className="btn-secondary"
                                    title="Regenerate from scratch"
                                >
                                    🔄 Regenerate
                                </button>
                            )}
                            <button
                                onClick={toggleEditMode}
                                className={`btn-secondary ${editMode ? '' : ''}`}
                                style={editMode ? {
                                    color: '#1a5aff', borderColor: 'rgba(26,90,255,0.5)',
                                    background: 'rgba(26,90,255,0.08)',
                                } : {}}
                            >
                                {editMode ? '✏️ Editing' : '✏️ Edit'}
                            </button>
                            <button
                                onClick={handleFinalize}
                                disabled={loading}
                                className="btn-primary"
                                style={{ padding: '10px 20px', position: 'relative' }}
                            >
                                {loading ? '⏳ Rendering…' : '📑 Finalize PDF'}
                                {hasEdits && !loading && (
                                    <span style={{
                                        position: 'absolute', top: -4, right: -4,
                                        width: 10, height: 10, borderRadius: '50%',
                                        background: '#ff4444', border: '2px solid var(--bg)',
                                    }} />
                                )}
                            </button>
                            {pdfUrl && (
                                <button
                                    onClick={() => window.open(pdfUrl, '_blank')}
                                    className="btn-primary"
                                    style={{ padding: '10px 20px', background: 'var(--green)', color: '#000' }}
                                >
                                    📥 Download PDF
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Status bar */}
            {status && (
                <div className="card" style={{
                    padding: '10px 18px',
                    borderColor: status.startsWith('Error') ? 'rgba(255,68,68,0.3)'
                        : status.includes('⚠️') ? 'rgba(255,200,0,0.3)'
                        : 'rgba(0,255,136,0.2)',
                }}>
                    <p className="mono" style={{
                        fontSize: '0.78rem',
                        color: status.startsWith('Error') ? 'var(--red)'
                            : status.includes('⚠️') ? '#ffc800'
                            : 'var(--green)',
                    }}>
                        {status}
                    </p>
                </div>
            )}

            {/* Loading indicator */}
            {loading && !previewHtml && (
                <div className="card" style={{ padding: '60px 40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: 16, animation: 'pulse 1.5s ease-in-out infinite' }}>⏳</div>
                    <h3 style={{ fontSize: '1.2rem', letterSpacing: '-0.03em', marginBottom: 8 }}>
                        Generating Order…
                    </h3>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
                        This may take a few minutes for the full Gemini generation.
                    </p>
                </div>
            )}

            {/* Full-width Preview */}
            {previewHtml && (
                <div className="card" style={{ padding: 0, overflow: 'hidden', flex: 1, minHeight: '80vh' }}>
                    <div style={{
                        background: editMode ? 'rgba(26,90,255,0.06)' : 'rgba(191,255,0,0.04)',
                        borderBottom: '1px solid var(--border)',
                        padding: '10px 16px',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="mono-wide" style={{
                                fontSize: '9px',
                                color: editMode ? '#1a5aff' : 'var(--accent)',
                            }}>
                                {editMode ? '✏️ EDITING — Click any text or table cell' : '📄 PREVIEW'}
                            </span>
                        </div>
                        {hasEdits && (
                            <span className="mono" style={{ fontSize: '0.65rem', color: '#ff4444' }}>
                                ● UNSAVED EDITS
                            </span>
                        )}
                    </div>
                    <iframe
                        ref={iframeRef}
                        srcDoc={previewHtml}
                        style={{
                            width: '100%', height: 'calc(100% - 40px)',
                            border: 'none', background: '#fff',
                            minHeight: '75vh',
                        }}
                        title="Order Preview"
                        sandbox="allow-same-origin allow-scripts"
                    />
                </div>
            )}

            {/* Empty state */}
            {!previewHtml && !loading && (
                <div className="card" style={{ padding: '60px 40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: 16 }}>📄</div>
                    <h3 style={{ fontSize: '1.2rem', letterSpacing: '-0.03em', marginBottom: 8 }}>
                        Ready to Draft
                    </h3>
                    <p className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
                        Click "Generate Draft" to create the KSERC truing-up order from your analysis results.
                    </p>
                </div>
            )}
        </section>
    )
}
