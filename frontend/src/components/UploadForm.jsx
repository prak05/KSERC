import { useState, useRef } from 'react'

export default function UploadForm({ licensees, financialYears, onSubmit }) {
    const [file, setFile] = useState(null)
    const [licensee, setLicensee] = useState('')
    const [year, setYear] = useState('')
    const [isDragOver, setIsDragOver] = useState(false)
    const fileRef = useRef(null)

    const isReady = file && licensee && year

    const handleDrop = (e) => {
        e.preventDefault()
        setIsDragOver(false)
        const f = e.dataTransfer.files[0]
        if (f && f.type === 'application/pdf') setFile(f)
    }

    const handleFileChange = (e) => {
        const f = e.target.files[0]
        if (f) setFile(f)
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!isReady) return
        const fd = new FormData()
        fd.append('file', file)
        fd.append('licensee', licensee)
        fd.append('financial_year', year)
        onSubmit(fd)
    }

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    return (
        <section className="animate-fade-in-up">
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-kserc-navy">Submit Petition for Truing Up Analysis</h2>
                <p className="text-kserc-text-muted mt-1">
                    Upload the licensee's petition PDF for automated compliance analysis against KSERC Regulations, 2021
                </p>
            </div>

            <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-kserc-border p-8 space-y-8">

                {/* Licensee + Year */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="flex items-center gap-2 text-sm font-semibold text-kserc-navy mb-2">
                            <span>🏢</span> Small Distribution Licensee
                        </label>
                        <select
                            value={licensee}
                            onChange={(e) => setLicensee(e.target.value)}
                            required
                            className="w-full px-4 py-3 rounded-lg border border-kserc-border bg-white text-kserc-text focus:outline-none focus:ring-2 focus:ring-kserc-navy/20 focus:border-kserc-navy transition-all"
                        >
                            <option value="">— Select Licensee —</option>
                            {licensees.map((l) => (
                                <option key={l} value={l}>{l}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="flex items-center gap-2 text-sm font-semibold text-kserc-navy mb-2">
                            <span>📅</span> Financial Year
                        </label>
                        <select
                            value={year}
                            onChange={(e) => setYear(e.target.value)}
                            required
                            className="w-full px-4 py-3 rounded-lg border border-kserc-border bg-white text-kserc-text focus:outline-none focus:ring-2 focus:ring-kserc-navy/20 focus:border-kserc-navy transition-all"
                        >
                            <option value="">— Select Year —</option>
                            {financialYears.map((y) => (
                                <option key={y} value={y}>{y}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Drop Zone */}
                <div
                    onDrop={handleDrop}
                    onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                    onDragLeave={() => setIsDragOver(false)}
                    onClick={() => fileRef.current?.click()}
                    className={`relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-300 ${isDragOver
                            ? 'border-kserc-navy bg-kserc-navy/5 scale-[1.01]'
                            : file
                                ? 'border-kserc-green/40 bg-kserc-green/5'
                                : 'border-kserc-border hover:border-kserc-navy/40 hover:bg-kserc-navy/[0.02]'
                        }`}
                >
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="hidden"
                    />

                    {!file ? (
                        <div className="space-y-3">
                            <div className="text-5xl opacity-60">📄</div>
                            <h3 className="text-lg font-semibold text-kserc-navy">Upload Petition PDF</h3>
                            <p className="text-kserc-text-muted text-sm">Drag & drop your file here or click to browse</p>
                            <p className="text-kserc-text-muted/60 text-xs">Maximum file size: 50MB • PDF format only</p>
                        </div>
                    ) : (
                        <div className="flex items-center justify-center gap-4" onClick={(e) => e.stopPropagation()}>
                            <span className="text-3xl">📎</span>
                            <div className="text-left">
                                <p className="font-semibold text-kserc-navy">{file.name}</p>
                                <p className="text-xs text-kserc-text-muted">{formatSize(file.size)}</p>
                            </div>
                            <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); setFile(null) }}
                                className="ml-4 w-8 h-8 rounded-full bg-red-50 text-kserc-red hover:bg-red-100 transition-colors flex items-center justify-center text-lg font-bold"
                            >
                                ✕
                            </button>
                        </div>
                    )}
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={!isReady}
                    className={`w-full py-4 rounded-xl text-white font-bold text-base tracking-wide transition-all duration-300 ${isReady
                            ? 'bg-gradient-to-r from-kserc-navy to-kserc-blue hover:from-kserc-navy-light hover:to-kserc-blue-light shadow-lg shadow-kserc-navy/20 hover:shadow-xl hover:scale-[1.01] active:scale-[0.99]'
                            : 'bg-gray-300 cursor-not-allowed'
                        }`}
                >
                    ⚡ Begin Analysis
                </button>
            </form>
        </section>
    )
}
