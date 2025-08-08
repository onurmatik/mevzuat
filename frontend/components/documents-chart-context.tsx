"use client"

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react"
import { DateRange } from "react-day-picker"
import { ChartConfig } from "@/components/ui/chart"

export type RangeOption =
  | "all"
  | "thisYear"
  | "lastYear"
  | "30days"
  | "custom"

interface DocumentsChartContextValue {
  config: ChartConfig
  visible: Record<string, boolean>
  toggleVisible: (key: string) => void
  rangeOption: RangeOption
  setRangeOption: (r: RangeOption) => void
  customRange: DateRange | undefined
  setCustomRange: (r: DateRange | undefined) => void
  typeLabelToId: Record<string, number>
}

const DocumentsChartContext = createContext<DocumentsChartContextValue | undefined>(
  undefined,
)

export function DocumentsChartProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ChartConfig>({})
  const [visible, setVisible] = useState<Record<string, boolean>>({})
  const [typeLabelToId, setTypeLabelToId] = useState<Record<string, number>>({})
  const [rangeOption, setRangeOption] = useState<RangeOption>("all")
  const [customRange, setCustomRange] = useState<DateRange | undefined>()

  useEffect(() => {
    async function loadTypes() {
      try {
        const typesRes = await fetch("/api/documents/types")
        const typeList: { id: number; label: string }[] = await typesRes.json()

        const typeMap: Record<string, number> = {}
        typeList.forEach(({ id, label }) => {
          typeMap[label] = id
        })
        setTypeLabelToId(typeMap)

        const palette = [
          "var(--chart-1)",
          "var(--chart-2)",
          "var(--chart-3)",
          "var(--chart-4)",
          "var(--chart-5)",
          "var(--chart-6)",
          "var(--chart-7)",
          "var(--chart-8)",
          "var(--chart-9)",
          "var(--chart-10)",
        ]

        const cfg: ChartConfig = {}
        const visibility: Record<string, boolean> = {}
        typeList.forEach(({ label }, idx) => {
          cfg[label] = { label, color: palette[idx % palette.length] }
          visibility[label] = true
        })
        setConfig(cfg)
        setVisible(visibility)
      } catch (err) {
        console.error(err)
      }
    }
    loadTypes()
  }, [])

  const toggleVisible = (key: string) =>
    setVisible((p) => ({ ...p, [key]: !p[key] }))

  return (
    <DocumentsChartContext.Provider
      value={{
        config,
        visible,
        toggleVisible,
        rangeOption,
        setRangeOption,
        customRange,
        setCustomRange,
        typeLabelToId,
      }}
    >
      {children}
    </DocumentsChartContext.Provider>
  )
}

export function useDocumentsChart() {
  const ctx = useContext(DocumentsChartContext)
  if (!ctx) {
    throw new Error("useDocumentsChart must be used within DocumentsChartProvider")
  }
  return ctx
}

