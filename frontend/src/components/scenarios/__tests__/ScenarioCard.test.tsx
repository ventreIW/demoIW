import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import ScenarioCard from "../ScenarioCard"
import type { ScenarioSummary } from "@/types/scenario"

const mockScenario: ScenarioSummary = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Caso 1 — Manufactura",
  sector: "manufacturing",
  status: "inactive",
  client_count: 0,
  created_at: "2026-06-25T10:00:00Z",
}

const activeScenario: ScenarioSummary = {
  ...mockScenario,
  id: "660e8400-e29b-41d4-a716-446655440001",
  name: "Caso 2 — Retail",
  sector: "retail",
  status: "active",
  client_count: 5,
}

describe("ScenarioCard", () => {
  it("renders name, sector badge, and Seleccionar button for inactive scenario", () => {
    render(
      <ScenarioCard
        scenario={mockScenario}
        isActive={false}
        onActivate={vi.fn()}
        isActivating={false}
      />,
    )

    expect(screen.getByText("Caso 1 — Manufactura")).toBeDefined()
    expect(screen.getByText("manufacturing")).toBeDefined()
    expect(screen.getByText("Sin datos")).toBeDefined()
    expect(screen.getByText("Seleccionar")).toBeDefined()
  })

  it("renders Activo badge and no Seleccionar button for active scenario", () => {
    render(
      <ScenarioCard
        scenario={activeScenario}
        isActive={true}
        onActivate={vi.fn()}
        isActivating={false}
      />,
    )

    const activoElements = screen.getAllByText("Activo")
    expect(activoElements.length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText("Seleccionar")).toBeNull()
  })

  it("calls onActivate when Seleccionar button is clicked", () => {
    const onActivate = vi.fn()
    render(
      <ScenarioCard
        scenario={mockScenario}
        isActive={false}
        onActivate={onActivate}
        isActivating={false}
      />,
    )

    fireEvent.click(screen.getByText("Seleccionar"))
    expect(onActivate).toHaveBeenCalledWith(mockScenario.id)
  })

  it("shows loading state when isActivating is true", () => {
    render(
      <ScenarioCard
        scenario={mockScenario}
        isActive={false}
        onActivate={vi.fn()}
        isActivating={true}
      />,
    )

    const button = screen.getByRole("button")
    expect(button).toBeDefined()
    expect((button as HTMLButtonElement).disabled).toBe(true)
  })
})