import { useEffect, useState } from 'react'

export default function LoadingScreen({ progressLogs = [] }) {
    const [dots, setDots] = useState('')

    useEffect(() => {
        const iv = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 400)
        return () => clearInterval(iv)
    }, [])

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 9000,
            background: 'var(--bg)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            overflow: 'hidden',
        }}>
            {/* Inject all loader CSS */}
            <style>{`
                /* ─── Speeder Loader ─────────────────────── */
                .speeder-loader {
                    position: relative;
                    animation: speeder 0.4s linear infinite;
                }
                .speeder-loader > span {
                    height: 5px; width: 35px;
                    background: var(--accent);
                    position: absolute; top: -19px; left: 60px;
                    border-radius: 2px 10px 1px 0;
                }
                .speeder-base span {
                    position: absolute; width: 0; height: 0;
                    border-top: 6px solid transparent;
                    border-right: 100px solid var(--accent);
                    border-bottom: 6px solid transparent;
                }
                .speeder-base span::before {
                    content: ""; position: absolute;
                    height: 22px; width: 22px; border-radius: 50%;
                    background: var(--accent);
                    right: -110px; top: -16px;
                }
                .speeder-base span::after {
                    content: ""; position: absolute;
                    width: 0; height: 0;
                    border-top: 0 solid transparent;
                    border-right: 55px solid var(--accent);
                    border-bottom: 16px solid transparent;
                    top: -16px; right: -98px;
                }
                .speeder-face {
                    position: absolute;
                    height: 12px; width: 20px;
                    background: var(--accent);
                    border-radius: 20px 20px 0 0;
                    transform: rotate(-40deg);
                    right: -125px; top: -15px;
                }
                .speeder-face::after {
                    content: ""; position: absolute;
                    height: 12px; width: 12px;
                    background: var(--accent);
                    right: 4px; top: 7px;
                    transform: rotate(40deg);
                    transform-origin: 50% 50%;
                    border-radius: 0 0 0 2px;
                }

                /* Speed lines off the loader */
                .speeder-loader > span > span:nth-child(1),
                .speeder-loader > span > span:nth-child(2),
                .speeder-loader > span > span:nth-child(3),
                .speeder-loader > span > span:nth-child(4) {
                    width: 30px; height: 1px;
                    background: var(--accent);
                    position: absolute;
                    animation: fazer1 0.2s linear infinite;
                }
                .speeder-loader > span > span:nth-child(2) { top: 3px; animation: fazer2 0.4s linear infinite; }
                .speeder-loader > span > span:nth-child(3) { top: 1px; animation: fazer3 0.4s linear infinite; animation-delay: -1s; }
                .speeder-loader > span > span:nth-child(4) { top: 4px; animation: fazer4 1s linear infinite; animation-delay: -1s; }

                @keyframes fazer1 { 0% { left: 0; } 100% { left: -80px; opacity: 0; } }
                @keyframes fazer2 { 0% { left: 0; } 100% { left: -100px; opacity: 0; } }
                @keyframes fazer3 { 0% { left: 0; } 100% { left: -50px; opacity: 0; } }
                @keyframes fazer4 { 0% { left: 0; } 100% { left: -150px; opacity: 0; } }

                @keyframes speeder {
                    0%   { transform: translate(2px, 1px) rotate(0deg); }
                    10%  { transform: translate(-1px, -3px) rotate(-1deg); }
                    20%  { transform: translate(-2px, 0px) rotate(1deg); }
                    30%  { transform: translate(1px, 2px) rotate(0deg); }
                    40%  { transform: translate(1px, -1px) rotate(1deg); }
                    50%  { transform: translate(-1px, 3px) rotate(-1deg); }
                    60%  { transform: translate(-1px, 1px) rotate(0deg); }
                    70%  { transform: translate(3px, 1px) rotate(-1deg); }
                    80%  { transform: translate(-2px, -1px) rotate(1deg); }
                    90%  { transform: translate(2px, 1px) rotate(0deg); }
                    100% { transform: translate(1px, -2px) rotate(-1deg); }
                }

                /* ─── Long Fazers (background streaks) ────── */
                .long-fazers {
                    position: absolute; inset: 0;
                    overflow: hidden; pointer-events: none;
                }
                .long-fazers span {
                    position: absolute; height: 2px; width: 20%;
                    background: linear-gradient(90deg, transparent, var(--accent), transparent);
                    opacity: 0.08;
                }
                .long-fazers span:nth-child(1) { top: 20%; animation: lf 0.6s linear infinite; animation-delay: -5s; }
                .long-fazers span:nth-child(2) { top: 40%; animation: lf2 0.8s linear infinite; animation-delay: -1s; }
                .long-fazers span:nth-child(3) { top: 60%; animation: lf3 0.6s linear infinite; }
                .long-fazers span:nth-child(4) { top: 80%; animation: lf4 0.5s linear infinite; animation-delay: -3s; }

                @keyframes lf  { 0% { left: 200%; } 100% { left: -200%; opacity: 0; } }
                @keyframes lf2 { 0% { left: 200%; } 100% { left: -200%; opacity: 0; } }
                @keyframes lf3 { 0% { left: 200%; } 100% { left: -100%; opacity: 0; } }
                @keyframes lf4 { 0% { left: 200%; } 100% { left: -100%; opacity: 0; } }

                /* ─── Progress bar sweep ─────────────────── */
                @keyframes progress-sweep {
                    0%   { transform: translateX(-100%); }
                    50%  { transform: translateX(50%); }
                    100% { transform: translateX(200%); }
                }

                /* ─── Pulse text ─────────────────────────── */
                @keyframes text-pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                /* ─── Log entry slide in ─────────────────── */
                @keyframes log-slide {
                    from { opacity: 0; transform: translateX(20px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
            `}</style>

            {/* Background streaks */}
            <div className="long-fazers">
                <span /><span /><span /><span />
            </div>

            {/* Glow blobs */}
            <div style={{ position: 'absolute', width: 500, height: 500, top: '-15%', right: '-10%', borderRadius: '50%', filter: 'blur(150px)', background: 'var(--accent)', opacity: 0.06, pointerEvents: 'none' }} />
            <div style={{ position: 'absolute', width: 400, height: 400, bottom: '-10%', left: '-8%', borderRadius: '50%', filter: 'blur(150px)', background: 'var(--accent)', opacity: 0.04, pointerEvents: 'none' }} />

            {/* Speeder character */}
            <div style={{ position: 'relative', width: '100%', maxWidth: 500, height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div className="speeder-loader">
                    <span>
                        <span /><span /><span /><span />
                    </span>
                    <div className="speeder-base">
                        <span />
                        <div className="speeder-face" />
                    </div>
                </div>
            </div>

            {/* Title + subtitle */}
            <div style={{ textAlign: 'center', zIndex: 10, marginTop: 16 }}>
                <h1 style={{
                    fontFamily: 'var(--font-display)', fontWeight: 800,
                    fontSize: 'clamp(1.4rem, 4vw, 2.2rem)',
                    letterSpacing: '-0.05em', textTransform: 'uppercase',
                    color: 'var(--text)', lineHeight: 1,
                    animation: 'text-pulse 2s ease-in-out infinite',
                }}>
                    Processing Petition{dots}
                </h1>
                <p style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px',
                    fontWeight: 500, letterSpacing: '0.4em', textTransform: 'uppercase',
                    color: 'var(--text-secondary)', marginTop: 12,
                }}>
                    KSERC Audit Pipeline Running
                </p>
            </div>

            {/* Progress bar */}
            <div style={{
                width: 280, height: 3, background: 'rgba(255,255,255,0.06)',
                borderRadius: 999, marginTop: 28, overflow: 'hidden', position: 'relative',
            }}>
                <div style={{
                    height: '100%', width: '33%',
                    background: 'var(--accent)',
                    borderRadius: 999,
                    animation: 'progress-sweep 3s ease-in-out infinite',
                    boxShadow: '0 0 12px var(--accent-glow)',
                }} />
            </div>

            {/* Progress log entries */}
            {progressLogs.length > 0 && (
                <div style={{
                    marginTop: 32, width: '90%', maxWidth: 520,
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '16px 20px',
                    maxHeight: 200, overflowY: 'auto',
                    zIndex: 10,
                }}>
                    {progressLogs.map((log, i) => (
                        <div key={i} style={{
                            display: 'flex', gap: 12, padding: '5px 0',
                            borderBottom: i < progressLogs.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                            animation: 'log-slide 0.4s var(--ease-expo) forwards',
                            animationDelay: `${i * 0.05}s`,
                            opacity: 0,
                        }}>
                            <span style={{
                                fontFamily: 'var(--font-mono)', fontSize: '10px',
                                fontWeight: 600, letterSpacing: '0.2em',
                                color: 'var(--accent)', flexShrink: 0,
                            }}>
                                {String(log.step).padStart(2, '0')}
                            </span>
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                                {log.message}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Bottom decorative elements */}
            <div style={{
                position: 'absolute', bottom: 32, left: 32,
                display: 'flex', flexDirection: 'column', gap: 6, opacity: 0.35,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600, letterSpacing: '0.3em', textTransform: 'uppercase', color: 'var(--text)' }}>
                        SYSTEMS NOMINAL
                    </span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.1em', color: 'var(--text-secondary)' }}>
                    KSERC SDL // TRUING UP ENGINE v2.0
                </span>
            </div>

            <div style={{
                position: 'absolute', top: 32, right: 32,
                textAlign: 'right', opacity: 0.35,
            }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600, letterSpacing: '0.3em', textTransform: 'uppercase', color: 'var(--text)' }}>
                    LATENCY: 14ms
                </span>
            </div>

            {/* Top-left branding */}
            <div style={{
                position: 'absolute', top: 28, left: 32,
                display: 'flex', alignItems: 'center', gap: 14,
            }}>
                <img src="/kserc-logo.png" alt="KSERC" style={{
                    width: 44, height: 44, borderRadius: '50%',
                    border: '2px solid rgba(255,255,255,0.15)',
                    boxShadow: '0 0 20px rgba(191,255,0,0.1)',
                }} />
                <div>
                    <span style={{
                        fontFamily: 'var(--font-display)', fontSize: '1rem',
                        fontWeight: 800, letterSpacing: '-0.03em', textTransform: 'uppercase',
                        display: 'block', lineHeight: 1.1,
                    }}>KSERC</span>
                    <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '8px',
                        fontWeight: 500, letterSpacing: '0.15em', textTransform: 'uppercase',
                        color: 'var(--text-secondary)', display: 'block', marginTop: 2,
                    }}>Truing-Up Engine</span>
                </div>
            </div>

            {/* Bottom-right process note */}
            <p style={{
                position: 'absolute', bottom: 32, right: 32,
                fontFamily: 'var(--font-mono)', fontSize: '9px',
                color: 'var(--text-tertiary)', letterSpacing: '0.15em', textTransform: 'uppercase',
                maxWidth: 250, textAlign: 'right', lineHeight: 1.6,
            }}>
                This may take 2–5 minutes depending on document complexity.
            </p>
        </div>
    )
}
