'use client'

import { useRef, useState } from 'react'
import { uploadCsv } from '@/lib/api/scenarios'

interface CsvUploadProps {
  onUploadComplete: () => void
}

export default function CsvUpload({ onUploadComplete }: CsvUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    setError(null)
    setSuccess(null)
  }

  function handleSelectClick() {
    fileInputRef.current?.click()
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError(null)
    setSuccess(null)
    try {
      const scenario = await uploadCsv(file)
      setSuccess(`Escenario "${scenario.name}" creado correctamente.`)
      setFile(null)
      onUploadComplete()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al subir el archivo.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        aria-label="Seleccionar archivo CSV"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="flex items-center gap-2">
        {!file ? (
          <button
            type="button"
            onClick={handleSelectClick}
            disabled={uploading}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Subir CSV
          </button>
        ) : (
          <>
            <span className="max-w-[200px] truncate text-sm text-slate-600">{file.name}</span>
            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading}
              className="inline-flex h-8 items-center justify-center rounded-lg border border-transparent bg-slate-800 px-3 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {uploading ? 'Subiendo...' : 'Subir'}
            </button>
            <button
              type="button"
              onClick={() => {
                setFile(null)
                setError(null)
                setSuccess(null)
              }}
              disabled={uploading}
              className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-300 bg-white px-2 text-sm text-slate-500 hover:text-slate-700 disabled:opacity-50"
              aria-label="Cancelar seleccion"
            >
              ✕
            </button>
          </>
        )}
      </div>

      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  )
}
