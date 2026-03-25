const TABS = [
    { id: 'upload', label: '↑ Submit', icon: '01' },
    { id: 'results', label: '◆ Audit Results', icon: '02' },
    { id: 'reference', label: '■ Reference Data', icon: '03' },
    { id: 'regulations', label: '⚖ Regulations', icon: '04' },
]

export default function Navigation({ activeView, onNavigate, hasResults }) {
    return (
        <nav className="animate-slide-up delay-1" style={{
            display: 'flex', gap: 0, marginTop: 20, marginBottom: 32,
            borderBottom: '1px solid var(--border)',
        }}>
            {TABS.map(tab => {
                const isActive = activeView === tab.id
                const isDisabled = tab.id === 'results' && !hasResults
                return (
                    <button
                        key={tab.id}
                        onClick={() => !isDisabled && onNavigate(tab.id)}
                        disabled={isDisabled}
                        style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '10px',
                            fontWeight: 600,
                            letterSpacing: '0.2em',
                            textTransform: 'uppercase',
                            padding: '14px 24px',
                            background: 'transparent',
                            border: 'none',
                            borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                            color: isActive ? 'var(--accent)' : isDisabled ? 'var(--text-tertiary)' : 'var(--text-secondary)',
                            cursor: isDisabled ? 'not-allowed' : 'pointer',
                            transition: 'all 0.3s var(--ease-expo)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                        }}
                    >
                        <span style={{ opacity: 0.4, fontSize: '9px', letterSpacing: '0.1em' }}>{tab.icon}</span>
                        {tab.label}
                    </button>
                )
            })}
        </nav>
    )
}
