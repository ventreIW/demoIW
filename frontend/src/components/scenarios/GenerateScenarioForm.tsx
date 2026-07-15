'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { generateScenario, activateScenario } from '@/lib/api/scenarios'
import type { ScenarioSummary, Sector } from '@/types/scenario'

const SECTORS: { value: Sector; label: string }[] = [
  { value: 'manufacturing', label: 'Manufactura' },
  { value: 'retail', label: 'Retail' },
  { value: 'professional_services', label: 'Servicios Profesionales' },
]

export default function GenerateScenarioForm() {
  const router = useRouter()

  const [sector, setSector] = useState<Sector>('manufacturing')
  const [clientCount, setClientCount] = useState(100)
  const [invoiceVolume, setInvoiceVolume] = useState(3)
  const [amountMean, setAmountMean] = useState(15000)
  const [amountStd, setAmountStd] = useState(8000)
  const [seed, setSeed] = useState<number | undefined>(undefined)
  const [generating, setGenerating] = useState(false)
  const [scenario, setScenario] = useState<ScenarioSummary | null>(null)
  const [activating, setActivating] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setGenerating(true)
    setScenario(null)

    try {
      const result = await generateScenario({
        sector,
        client_count: clientCount,
        invoice_volume: invoiceVolume,
        amount_mean: amountMean,
        amount_std: amountStd,
        seed,
        reference_date: null,
      })

      setScenario(result)
      router.replace(`/scenarios/generate?scenarioId=${result.id}`, { scroll: false })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al generar el escenario')
    } finally {
      setGenerating(false)
    }
  }

  async function handleActivate() {
    if (!scenario) return
    setActivating(true)
    try {
      await activateScenario(scenario.id)
      router.push('/operations')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error al activar el escenario')
    } finally {
      setActivating(false)
    }
  }

  async function handleCopyId() {
    if (!scenario) return
    try {
      await navigator.clipboard.writeText(scenario.id)
      toast.success('ID copiado al portapapeles')
    } catch {
      toast.error('No se pudo copiar el ID')
    }
  }

  return (
    <div className="space-y-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Sector */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">Sector</label>
          <Select value={sector} onValueChange={(v) => setSector(v as Sector)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SECTORS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Número de clientes */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor="clientCount">
            Número de clientes
          </label>
          <Input
            id="clientCount"
            type="number"
            min={10}
            max={500}
            value={clientCount}
            onChange={(e) => setClientCount(Number(e.target.value))}
            disabled={generating}
          />
          <p className="text-xs text-slate-400">Mínimo 10, máximo 500</p>
        </div>

        {/* Facturas por cliente */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor="invoiceVolume">
            Facturas por cliente
          </label>
          <Input
            id="invoiceVolume"
            type="number"
            min={1}
            max={10}
            value={invoiceVolume}
            onChange={(e) => setInvoiceVolume(Number(e.target.value))}
            disabled={generating}
          />
          <p className="text-xs text-slate-400">Mínimo 1, máximo 10</p>
        </div>

        {/* Semilla */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700" htmlFor="seed">
            Semilla (opcional)
          </label>
          <Input
            id="seed"
            type="number"
            placeholder="Auto"
            value={seed ?? ''}
            onChange={(e) => {
              const v = e.target.value
              setSeed(v === '' ? undefined : Number(v))
            }}
            disabled={generating}
          />
          <p className="text-xs text-slate-400">
            Misma semilla = mismos datos. Vacío para semilla aleatoria.
          </p>
        </div>

        {/* Submit */}
        <Button type="submit" disabled={generating} className="w-full" size="lg">
          {generating ? (
            <span className="flex items-center gap-2">
              <Spinner />
              Generando datos...
            </span>
          ) : (
            'Generar escenario'
          )}
        </Button>
      </form>

      {/* Results section */}
      {scenario && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-900">Escenario generado</h2>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Nombre:</span>
              <p className="font-medium text-slate-900">{scenario.name}</p>
            </div>
            <div>
              <span className="text-slate-500">Sector:</span>
              <p className="font-medium text-slate-900">{scenario.sector}</p>
            </div>
            <div>
              <span className="text-slate-500">Clientes:</span>
              <p className="font-medium text-slate-900">{scenario.client_count}</p>
            </div>
            <div>
              <span className="text-slate-500">Estado:</span>
              <p className="font-medium text-slate-900 capitalize">
                {scenario.status === 'active' ? 'Activo' : 'Inactivo'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Creado:</span>
              <p className="font-medium text-slate-900">
                {new Date(scenario.created_at).toLocaleDateString('es-MX')}
              </p>
            </div>
            <div>
              <span className="text-slate-500">ID:</span>
              <p className="font-mono text-xs text-slate-900 truncate">{scenario.id}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <Button variant="outline" size="sm" onClick={handleCopyId}>
              Copiar ID
            </Button>

            <a
              href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/scenarios/${scenario.id}/download`}
              download
            >
              <Button variant="outline" size="sm" type="button">
                Descargar JSON
              </Button>
            </a>

            <Button
              size="sm"
              disabled={activating}
              onClick={handleActivate}
            >
              {activating ? 'Activando...' : 'Activar y usar'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="size-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}