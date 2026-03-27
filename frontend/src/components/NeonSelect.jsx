import { useState, useRef, useEffect } from 'react'

export default function NeonSelect({ value, onChange, options, placeholder = 'Select...', style }) {
    const [open, setOpen] = useState(false)
    const ref = useRef(null)

    // Close on outside click
    useEffect(() => {
        const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    const selectedLabel = options.find(o => (typeof o === 'string' ? o : o.value) === value)
    const displayLabel = selectedLabel
        ? (typeof selectedLabel === 'string' ? selectedLabel : selectedLabel.label)
        : placeholder

    return (
        <div ref={ref} style={{ position: 'relative', ...style }}>
            {/* Trigger */}
            <button
                type="button"
                onClick={() => setOpen(o => !o)}
                style={{
                    width: '100%',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    letterSpacing: '0.05em',
                    padding: '12px 36px 12px 16px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: open ? '1px solid rgba(191, 255, 0, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '0.75rem',
                    color: value ? 'var(--text)' : 'var(--text-tertiary)',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                    boxShadow: open ? '0 0 15px rgba(191, 255, 0, 0.1)' : 'none',
                    position: 'relative',
                }}
            >
                {displayLabel}
                <span style={{
                    position: 'absolute', right: 14, top: '50%',
                    transform: `translateY(-50%) rotate(${open ? '180deg' : '0deg'})`,
                    transition: 'transform 0.2s ease',
                    fontSize: '10px', color: 'rgba(255,255,255,0.3)',
                }}>▾</span>
            </button>

            {/* Dropdown */}
            {open && (
                <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 4px)',
                    left: 0, right: 0,
                    zIndex: 1000,
                    background: '#111',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '0.75rem',
                    padding: '4px',
                    boxShadow: '0 12px 40px rgba(0,0,0,0.6), 0 0 20px rgba(191, 255, 0, 0.04)',
                    backdropFilter: 'blur(20px)',
                    animation: 'dropdown-open 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                    maxHeight: 260,
                    overflowY: 'auto',
                }}>
                    <style>{`
                        @keyframes dropdown-open {
                            from { opacity: 0; transform: translateY(-6px) scale(0.98); }
                            to { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                    {options.map((opt, i) => {
                        const optValue = typeof opt === 'string' ? opt : opt.value
                        const optLabel = typeof opt === 'string' ? opt : opt.label
                        const isSelected = optValue === value
                        return (
                            <button
                                key={optValue}
                                type="button"
                                onClick={() => { onChange(optValue); setOpen(false) }}
                                style={{
                                    width: '100%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 10,
                                    padding: '10px 14px',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    fontFamily: 'var(--font-mono)',
                                    fontSize: '11px',
                                    letterSpacing: '0.05em',
                                    background: isSelected ? 'rgba(191, 255, 0, 0.1)' : 'transparent',
                                    color: isSelected ? '#BFFF00' : 'rgba(255,255,255,0.7)',
                                    transition: 'all 0.15s ease',
                                }}
                                onMouseEnter={e => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                                        e.currentTarget.style.color = '#fff'
                                    }
                                }}
                                onMouseLeave={e => {
                                    if (!isSelected) {
                                        e.currentTarget.style.background = 'transparent'
                                        e.currentTarget.style.color = 'rgba(255,255,255,0.7)'
                                    }
                                }}
                            >
                                <span style={{
                                    fontFamily: 'var(--font-mono)', fontSize: '9px',
                                    color: 'rgba(255,255,255,0.2)', width: 16,
                                }}>{String(i + 1).padStart(2, '0')}</span>
                                {optLabel}
                                {isSelected && <span style={{ marginLeft: 'auto', color: '#BFFF00', fontSize: '10px' }}>✓</span>}
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
