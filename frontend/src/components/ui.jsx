/* Shared primitives for the KSERC interface. */

/** Off-white luxury CTA; label rolls up and the block inverts on hover. */
export function Cta({ children, block = false, className = '', ...props }) {
    return (
        <button className={`cta ${block ? 'cta-block' : ''} ${className}`} {...props}>
            <span className="cta-track">
                <span className="cta-roll">
                    <span>{children}</span>
                    <span aria-hidden="true">{children}</span>
                </span>
            </span>
        </button>
    )
}

const STATUS = {
    approved: ['pill-ok', 'Approved'],
    reduced: ['pill-bad', 'Reduced'],
    increased: ['pill-accent', 'Increased'],
    COMPLETED: ['pill-ok', 'Completed'],
    FAILED: ['pill-bad', 'Failed'],
    RUNNING: ['pill-accent', 'Running'],
    PENDING: ['pill-plain', 'Pending'],
    PENDING_RM_REVIEW: ['pill-warn', 'Awaiting review'],
}

export function StatusPill({ status }) {
    const [cls, label] = STATUS[status] || ['pill-plain', status ? String(status).toLowerCase() : '—']
    return <span className={`pill ${cls}`}>{label}</span>
}

export function PageHead({ eyebrow, title, lede, children }) {
    return (
        <header className="page-head enter-frame">
            <div>
                {eyebrow && <span className="label">{eyebrow}</span>}
                <h1 className="h1 enter-title">{title}</h1>
                {lede && <p className="lede" style={{ marginTop: 8 }}>{lede}</p>}
            </div>
            {children && <div className="row">{children}</div>}
        </header>
    )
}

export function Notice({ tone = 'info', children, onClose }) {
    return (
        <div className={`notice notice-${tone}`} role={tone === 'bad' ? 'alert' : 'status'}>
            <span style={{ flex: 1 }}>{children}</span>
            {onClose && <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Dismiss">Dismiss</button>}
        </div>
    )
}

export function Chevron({ open }) {
    return (
        <svg className={`chev ${open ? 'is-open' : ''}`} width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3.5 1.5L7 5l-3.5 3.5" />
        </svg>
    )
}

export function Check({ on }) {
    return (
        <span className={`check ${on ? 'is-on' : ''}`}>
            {on && <svg viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M2 5.2l2 2L8 3" /></svg>}
        </span>
    )
}
