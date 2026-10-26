import { useState, useCallback, useRef, useEffect } from 'react'
import { Notice, PageHead } from './ui'

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
                        [contenteditable="true"] { outline: 1px dashed rgba(94,106,210,0.35); outline-offset: 2px; cursor: text; }
                        [contenteditable="true"]:focus { outline: 1px solid #5E6AD2; background: rgba(94,106,210,0.05); }
                        td[contenteditable="true"], th[contenteditable="true"] { outline: 1px dashed rgba(94,106,210,0.25); outline-offset: 0; min-width: 30px; }
                        .edit-banner { position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: #08090A; color: #F7F8F8; padding: 7px 16px; font: 11px/1.4 ui-monospace, Menlo, monospace; letter-spacing: .08em; text-transform: uppercase; }
                        body { padding-top: 32px !important; }
                    `
                    doc.head.appendChild(style)

                    const banner = doc.createElement('div')
                    banner.className = 'edit-banner'
                    banner.textContent = 'Edit mode — click any text or table cell to edit'
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

    // ── Generate draft ─────────────────────────────────
    const handleGenerate = useCallback(async () => {
        setLoading(true)
        setStatus({ tone: 'info', text: 'Drafting the order. This usually takes two to three minutes.' })
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
            setStatus({ tone: 'ok', text: 'Draft ready. Review and edit the preview, then finalize the PDF.' })
        } catch (e) {
            setStatus({ tone: 'bad', text: e.message })
        } finally {
            setLoading(false)
        }
    }, [analysisId])

    // ── Finalize PDF from current (possibly edited) HTML ────────────
    const handleFinalize = useCallback(async () => {
        setLoading(true)
        setStatus({ tone: 'info', text: 'Rendering the PDF from your edited preview…' })
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
            setStatus({ tone: 'ok', text: 'PDF finalized with your edits.' })
        } catch (e) {
            setStatus({ tone: 'bad', text: e.message })
        } finally {
            setLoading(false)
        }
    }, [analysisId, getCurrentHtml])

    // No blob URL needed — we use srcdoc directly

    const licensee = analysisData?.licensee_name || ''
    const fy = analysisData?.financial_year || ''

    return (
        <section className="stack view">
            <PageHead eyebrow={`Order drafter${licensee ? ' · ' + licensee : ''}${fy ? ' · FY ' + fy : ''}`} title="Draft the Commission's order">
                <button className="btn btn-ghost" onClick={onBack}>Back to results</button>
                {!previewHtml && !loading && <button className="btn btn-accent" onClick={handleGenerate}>Generate draft</button>}
                {previewHtml && (
                    <>
                        {!loading && <button className="btn" onClick={handleGenerate} title="Regenerate from scratch">Regenerate</button>}
                        <button className={`btn ${editMode ? 'is-on' : ''}`} onClick={toggleEditMode}>{editMode ? 'Editing' : 'Edit'}</button>
                        <button className="btn" disabled={loading} onClick={handleFinalize}>
                            {hasEdits && !loading && <span className="dot" />}
                            {loading ? 'Rendering…' : 'Finalize PDF'}
                        </button>
                        <button className="btn" onClick={() => window.open(`/api/export-docx/${analysisId}`, '_blank')}>Export DOCX</button>
                        {pdfUrl && <button className="btn btn-accent" onClick={() => window.open(pdfUrl, '_blank')}>Download PDF</button>}
                    </>
                )}
            </PageHead>

            {status && <Notice tone={status.tone}>{status.text}</Notice>}

            {loading && !previewHtml && (
                <div className="card">
                    <div className="progress is-indeterminate"><span /></div>
                    <div className="empty"><p className="h3">Drafting…</p><p>Five sections are written in sequence against the reference order format.</p></div>
                </div>
            )}

            {previewHtml && (
                <div className="preview enter-panel">
                    <div className="card-head">
                        <span className="label">{editMode ? 'Editing — click any text or table cell' : 'Preview'}</span>
                        <span className="spacer" />
                        {hasEdits && <span className="pill pill-warn">Unsaved edits</span>}
                    </div>
                    <iframe ref={iframeRef} srcDoc={previewHtml} title="Order preview" sandbox="allow-same-origin allow-scripts" />
                </div>
            )}

            {!previewHtml && !loading && (
                <div className="card empty">
                    <p className="h3">Ready to draft</p>
                    <p>Generate the KSERC truing-up order from these analysis results. You can edit every paragraph and table before finalizing.</p>
                </div>
            )}
        </section>
    )
}
