export default function Header() {
    return (
        <header className="animate-slide-up" style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '28px 0', borderBottom: '1px solid var(--border)',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                {/* Logo mark */}
                <img src="/kserc-logo.png" alt="KSERC" style={{
                    width: 42, height: 42, borderRadius: '50%',
                    border: '2px solid rgba(191,255,0,0.3)',
                    boxShadow: '0 0 20px var(--accent-glow)',
                    objectFit: 'cover',
                }} />
                <div>
                    <p className="mono-wide" style={{ marginBottom: 2 }}>KSERC Regulatory Platform</p>
                    <h1 style={{
                        fontSize: 'clamp(1.3rem, 3vw, 1.8rem)',
                        lineHeight: 0.95, letterSpacing: '-0.05em',
                    }}>
                        Truing-Up<br />
                        <span style={{ color: 'var(--accent)' }}>Audit Engine</span>
                    </h1>
                </div>
            </div>
            <div style={{ textAlign: 'right', maxWidth: 280 }}>
                <p className="mono" style={{ lineHeight: 1.8 }}>
                    Automated compliance analysis under<br />
                    KSERC Regulations, 2021
                </p>
            </div>
        </header>
    )
}
