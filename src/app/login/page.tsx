"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LogIn, ShieldCheck } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [showPass, setShowPass] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username || !password) {
            setError("Please enter both username and password.");
            return;
        }
        setError("");
        setLoading(true);
        // Simulated auth — no real backend auth required
        await new Promise(res => setTimeout(res, 900));
        setLoading(false);
        router.push("/");
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-[#0F2238] relative overflow-hidden">
            {/* Subtle background pattern */}
            <div className="absolute inset-0 opacity-[0.04]" style={{
                backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 40px, #ffffff 40px, #ffffff 41px), repeating-linear-gradient(90deg, transparent, transparent 40px, #ffffff 40px, #ffffff 41px)'
            }} />

            {/* Glow orbs */}
            <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full bg-[#1A3557]/40 blur-3xl pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-[#C8960C]/10 blur-3xl pointer-events-none" />

            {/* Card */}
            <div className="relative z-10 w-full max-w-[440px] px-6">
                {/* Logos + Title */}
                <div className="flex justify-center items-center gap-4 mb-8">
                    <div className="flex flex-col items-center gap-1">
                        <div className="h-[64px] w-[64px] rounded-full bg-[#C8960C] flex items-center justify-center shadow-lg shadow-[#C8960C]/30 ring-2 ring-[#C8960C]/40">
                            <span className="font-serif text-[13px] font-black text-[#0F2238] leading-tight text-center">KSERC</span>
                        </div>
                    </div>
                    <div className="h-10 w-px bg-white/10" />
                    <div className="flex flex-col items-center gap-1">
                        <div className="h-[64px] w-[64px] rounded-full bg-white/10 border border-white/20 flex items-center justify-center shadow-lg">
                            <span className="font-serif text-[11px] font-bold text-white/80 leading-tight text-center">RIET</span>
                        </div>
                    </div>
                </div>

                <div className="text-center mb-8">
                    <h1 className="text-white font-serif text-[20px] font-semibold leading-snug tracking-tight">
                        Kerala State Electricity<br />Regulatory Commission
                    </h1>
                    <p className="text-[#C8960C] text-[11.5px] font-medium uppercase tracking-[1.6px] mt-2">
                        AI Truing-Up Analysis Tool
                    </p>
                </div>

                {/* Login Form */}
                <form
                    onSubmit={handleLogin}
                    className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 space-y-5 shadow-2xl"
                >
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/30 text-red-300 text-[13px] px-4 py-2.5 rounded-lg">
                            {error}
                        </div>
                    )}

                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-[1.2px] text-white/50 block">
                            Username
                        </label>
                        <input
                            id="username"
                            type="text"
                            autoComplete="username"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="Enter your username"
                            className="w-full h-11 bg-white/8 border border-white/15 rounded-lg px-4 text-[14px] text-white placeholder:text-white/25 focus:outline-none focus:border-[#C8960C]/70 focus:ring-1 focus:ring-[#C8960C]/30 transition-all"
                            style={{ background: 'rgba(255,255,255,0.05)' }}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-[1.2px] text-white/50 block">
                            Password
                        </label>
                        <div className="relative">
                            <input
                                id="password"
                                type={showPass ? "text" : "password"}
                                autoComplete="current-password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                className="w-full h-11 bg-white/8 border border-white/15 rounded-lg px-4 pr-11 text-[14px] text-white placeholder:text-white/25 focus:outline-none focus:border-[#C8960C]/70 focus:ring-1 focus:ring-[#C8960C]/30 transition-all"
                                style={{ background: 'rgba(255,255,255,0.05)' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPass(!showPass)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition-colors"
                            >
                                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <button
                        id="login-btn"
                        type="submit"
                        disabled={loading}
                        className="w-full h-12 bg-[#1A3557] hover:bg-[#243F6E] border border-[#2C6FAC]/40 text-white font-semibold text-[14px] rounded-lg flex items-center justify-center gap-2.5 transition-all duration-200 shadow-lg shadow-[#0F2238]/50 disabled:opacity-60 disabled:cursor-not-allowed mt-2"
                    >
                        {loading ? (
                            <>
                                <div className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                                Authenticating...
                            </>
                        ) : (
                            <>
                                <LogIn size={17} />
                                LOGIN TO KSERC PORTAL
                            </>
                        )}
                    </button>
                </form>

                {/* Footer */}
                <div className="mt-6 text-center space-y-2">
                    <div className="flex items-center justify-center gap-2 text-white/20 text-[11.5px]">
                        <ShieldCheck size={13} />
                        <span>Authorized access only. Work Order KSERC/CSO/03-05</span>
                    </div>
                    <p className="text-white/10 text-[10px] tracking-wider uppercase">
                        RIET ISR Project · v0.1
                    </p>
                </div>
            </div>
        </div>
    );
}
