export default function Footer() {
    return (
        <footer style={{
            borderTop: '1px solid var(--border)',
            padding: '24px 0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
        }}>
            <p className="mono" style={{ letterSpacing: '0.3em' }}>
                KSERC · Tariff Audit · 2024
            </p>
            <p className="mono" style={{ color: 'var(--text-tertiary)' }}>
                Built with Gemini Vision · FastAPI · React
            </p>
        </footer>
    )
}
