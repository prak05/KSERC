import { useState, useRef } from 'react'

const KNOWN_INFLATION_RATES = {
    '2024-25': 3.05,
    '2023-24': 6.50,
    '2022-23': 7.06,
    '2021-22': 6.15,
    '2020-21': 5.52,
    '2019-20': 4.08,
}

// BEE energy audit fee is auto-extracted from the petition PDF by the AI extractor

export default function UploadForm({ licensees, financialYears, onSubmit }) {
    const [files, setFiles] = useState([])
    const [licensee, setLicensee] = useState('')
    const [year, setYear] = useState('')
    const [inflationRate, setInflationRate] = useState('')
    const [isDragOver, setIsDragOver] = useState(false)
    const fileRef = useRef(null)

    const isReady = files.length > 0 && licensee && year
    const defaultRate = year ? (KNOWN_INFLATION_RATES[year] ?? null) : null
    const isOverridden = inflationRate !== ''
    const displayRate = isOverridden ? inflationRate : (defaultRate !== null ? String(defaultRate) : '')

    const handleYearChange = (e) => {
        setYear(e.target.value)
        setInflationRate('')
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setIsDragOver(false)
        // Fallback to extension check if mime type is missing or reports differently
        const dropped = Array.from(e.dataTransfer.files).filter(f =>
            f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
        )
        if (dropped.length) setFiles(prev => [...prev, ...dropped])
    }

    const handleFileChange = (e) => {
        const selected = Array.from(e.target.files).filter(f => f.name.toLowerCase().endsWith('.pdf'))
        if (selected.length) setFiles(prev => [...prev, ...selected])
        if (fileRef.current) fileRef.current.value = ''
    }

    const removeFile = (idx) => {
        setFiles(prev => prev.filter((_, i) => i !== idx))
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!isReady) return
        const fd = new FormData()
        files.forEach(f => fd.append('files', f))
        fd.append('licensee', licensee)
        fd.append('financial_year', year)
        const effectiveRate = isOverridden ? inflationRate : (defaultRate !== null ? String(defaultRate) : '')
        if (effectiveRate !== '') fd.append('inflation_rate', effectiveRate)
        onSubmit(fd)
    }

    const formatSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    return (
        <section className="animate-fade-in-up">
            <div className="mb-8 text-center sm:text-left">
                <h2 className="text-3xl font-bold text-white tracking-tight drop-shadow-md">Submit Petition for Truing Up Analysis</h2>
                <p className="text-kserc-text-muted mt-2 text-lg">
                    Upload the licensee petition PDF for automated compliance analysis against KSERC Regulations, 2021
                </p>
            </div>

            <form onSubmit={handleSubmit} className="bg-kserc-surface/60 backdrop-blur-2xl rounded-2xl shadow-2xl border border-kserc-border p-8 space-y-8 relative overflow-hidden">
                {/* Subtle top glow */}
                <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="flex items-center gap-2 text-sm font-semibold text-white/90 mb-2 tracking-wide">
                            Small Distribution Licensee
                        </label>
                        <select
                            value={licensee}
                            onChange={(e) => setLicensee(e.target.value)}
                            required
                            className="w-full px-4 py-3 rounded-xl border border-white/10 bg-black/20 text-white focus:outline-none focus:ring-2 focus:ring-kserc-blue/50 focus:border-kserc-blue/50 transition-all backdrop-blur-sm shadow-inner"
                        >
                            <option value="" className="bg-gray-900 text-white">-- Select Licensee --</option>
                            {licensees.map((l) => (
                                <option key={l} value={l} className="bg-gray-900 text-white">{l}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="flex items-center gap-2 text-sm font-semibold text-white/90 mb-2 tracking-wide">
                            Financial Year
                        </label>
                        <select
                            value={year}
                            onChange={handleYearChange}
                            required
                            className="w-full px-4 py-3 rounded-xl border border-white/10 bg-black/20 text-white focus:outline-none focus:ring-2 focus:ring-kserc-green/50 focus:border-kserc-green/50 transition-all backdrop-blur-sm shadow-inner"
                        >
                            <option value="" className="bg-gray-900 text-white">-- Select Year --</option>
                            {financialYears.map((y) => (
                                <option key={y} value={y} className="bg-gray-900 text-white">{y}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Inflation Rate Section */}
                <div className="rounded-xl border border-kserc-gold/30 bg-kserc-gold/5 backdrop-blur-sm p-6 relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-kserc-gold to-kserc-gold-dark" />
                    <p className="text-sm font-semibold text-white mb-2 tracking-wide flex items-center gap-2">
                        <span className="text-kserc-gold">📈</span> Actual O&M Inflation Rate (CPI 70% + WPI 30%)
                    </p>
                    <p className="text-xs text-white/60 mb-4 leading-relaxed max-w-3xl">
                        Per Annexure-7 (KSERC Tariff Regulations 2021), the actual CPI+WPI weighted inflation
                        rate is applied to escalate O&M norms (Employee Cost, R&M, A&G) at truing up.
                        {year && defaultRate !== null
                            ? ' System default for ' + year + ': ' + defaultRate + '%. Edit to override.'
                            : !year ? ' Select a Financial Year to see the default.' : ' No default - enter manually.'}
                    </p>
                    <div className="flex items-center gap-4 flex-wrap">
                        <div className="relative">
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                max="25"
                                value={displayRate}
                                onChange={(e) => setInflationRate(e.target.value)}
                                placeholder={defaultRate !== null ? String(defaultRate) : '0.00'}
                                className="w-36 px-4 py-2.5 pr-8 rounded-lg border border-white/10 bg-black/30 text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-kserc-gold/50 focus:border-kserc-gold/50 transition-all shadow-inner"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 font-bold text-sm pointer-events-none">%</span>
                        </div>
                        {isOverridden && defaultRate !== null && (
                            <button
                                type="button"
                                onClick={() => setInflationRate('')}
                                className="text-xs text-kserc-gold/80 hover:text-kserc-gold transition-colors underline underline-offset-2"
                            >
                                Reset to {defaultRate}%
                            </button>
                        )}
                        <span className="text-xs italic text-white/40 bg-white/5 px-2 py-1 rounded-md border border-white/5">
                            {isOverridden ? 'Custom: ' + inflationRate + '%' : (defaultRate !== null ? 'System default' : '')}
                        </span>
                    </div>
                </div>

                {/* File Drop Zone */}
                <div
                    onDrop={handleDrop}
                    onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                    onDragLeave={() => setIsDragOver(false)}
                    onClick={() => fileRef.current?.click()}
                    className={
                        'relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 group ' +
                        (isDragOver ? 'border-kserc-blue bg-kserc-blue/10 scale-[1.02]'
                            : files.length ? 'border-kserc-green/40 bg-kserc-green/10'
                                : 'border-white/20 bg-black/20 hover:border-kserc-blue/50 hover:bg-white/5')
                    }
                >
                    <input ref={fileRef} type="file" accept=".pdf" multiple onChange={handleFileChange} className="hidden" />
                    {files.length === 0 ? (
                        <div className="space-y-4">
                            <div className="text-6xl opacity-70 group-hover:scale-110 transition-transform duration-300 drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">📄</div>
                            <h3 className="text-xl font-semibold text-white tracking-wide">Upload Petition PDFs</h3>
                            <p className="text-white/60 text-sm">Drag and drop your files here or click to browse</p>
                            <div className="inline-block mt-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full">
                                <p className="text-white/40 text-xs tracking-wider">MAX 50MB PER PDF</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-2 w-full" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
                                <span className="text-sm font-semibold text-white tracking-wider uppercase">{files.length} file{files.length > 1 ? 's' : ''} selected</span>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); fileRef.current?.click() }}
                                    className="text-xs px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors border border-white/10"
                                >+ Add more</button>
                            </div>
                            {files.map((f, idx) => (
                                <div key={idx} className="flex items-center gap-4 bg-black/40 rounded-xl px-4 py-3 border border-white/10 hover:border-white/30 transition-colors group/file">
                                    <span className="text-2xl drop-shadow-md">📄</span>
                                    <div className="flex-1 text-left min-w-0">
                                        <p className="font-medium text-white text-sm truncate">{f.name}</p>
                                        <p className="text-xs text-white/50">{formatSize(f.size)}</p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => removeFile(idx)}
                                        className="w-8 h-8 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500 hover:text-white transition-all flex items-center justify-center text-sm flex-shrink-0 opacity-50 group-hover/file:opacity-100"
                                    >×</button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={!isReady}
                    className={
                        'w-full py-4 rounded-xl text-white font-bold text-base tracking-widest uppercase transition-all duration-500 relative overflow-hidden group ' +
                        (isReady
                            ? 'bg-kserc-blue/20 border border-kserc-blue/50 hover:bg-kserc-blue hover:border-kserc-blue hover:shadow-[0_0_30px_rgba(59,130,246,0.6)] hover:-translate-y-1'
                            : 'bg-white/5 border border-white/5 text-white/30 cursor-not-allowed')
                    }
                >
                    <span className="relative z-10 flex items-center justify-center gap-2">
                        <span>Begin Analysis</span>
                        {isReady && <span className="group-hover:translate-x-1 transition-transform">→</span>}
                    </span>
                    {isReady && (
                        <div className="absolute inset-0 -translate-x-full group-hover:animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                    )}
                </button>
            </form>
        </section>
    )
}
