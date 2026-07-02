'use client'

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { ScenarioSummary } from '@/types/scenario'

interface ScenarioCardProps {
  scenario: ScenarioSummary
  isActive: boolean
  onActivate: (id: string) => Promise<void>
  isActivating: boolean
}

const SECTOR_LABELS: Record<string, string> = {
  manufacturing: 'manufacturing',
  retail: 'retail',
  professional_services: 'professional_services',
}

function statusBadge(scenario: ScenarioSummary): { text: string; color: string } {
  if (scenario.status === 'active') {
    return { text: 'Activo', color: 'bg-green-100 text-green-800' }
  }
  if (scenario.client_count === 0) {
    return { text: 'Sin datos', color: 'bg-gray-100 text-gray-600' }
  }
  return { text: 'Con datos', color: 'bg-blue-100 text-blue-800' }
}

export default function ScenarioCard({
  scenario,
  isActive,
  onActivate,
  isActivating,
}: ScenarioCardProps) {
  const badge = statusBadge(scenario)
  const sectorLabel = SECTOR_LABELS[scenario.sector] ?? scenario.sector

  return (
    <Card className={isActive ? 'ring-primary ring-2' : ''}>
      <CardHeader>
        <CardTitle>{scenario.name}</CardTitle>
        <CardDescription>
          <span className="inline-block rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {sectorLabel}
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${badge.color}`}
          >
            {badge.text}
          </span>
          <span className="text-sm text-slate-500">{scenario.client_count} clientes</span>
        </div>
      </CardContent>
      <CardFooter>
        {isActive ? (
          <span className="text-primary text-sm font-medium">Activo</span>
        ) : (
          <Button onClick={() => onActivate(scenario.id)} disabled={isActivating} variant="default">
            {isActivating ? 'Activando...' : 'Seleccionar'}
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}
