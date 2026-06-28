"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import ScenarioCard from "./ScenarioCard"
import { activateScenario } from "@/lib/api/scenarios"
import type { ScenarioSummary } from "@/types/scenario"

interface ScenarioGridProps {
  scenarios: ScenarioSummary[]
  activeId: string | null
}

export default function ScenarioGrid({ scenarios, activeId }: ScenarioGridProps) {
  const router = useRouter()
  const [activatingId, setActivatingId] = useState<string | null>(null)

  async function handleActivate(id: string) {
    setActivatingId(id)
    try {
      await activateScenario(id)
      router.refresh()
    } catch {
      setActivatingId(null)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {scenarios.map((scenario) => (
        <ScenarioCard
          key={scenario.id}
          scenario={scenario}
          isActive={scenario.id === activeId}
          onActivate={handleActivate}
          isActivating={activatingId === scenario.id}
        />
      ))}
    </div>
  )
}