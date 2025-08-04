"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
// 🔹 Use TooltipProps from the component’s type declarations so `payload` is recognised
import type { TooltipProps } from "recharts/types/component/Tooltip"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartConfig } from "@/components/ui/chart"

interface Document {
  id: number
  name: string
  mevzuat_tur: number
  resmi_gazete_tarihi?: string
}

const typeLabelToId: Record<string, number> = {
  Kanun: 1,
  KHK: 4,
  "Cumhurbaşkanlığı Kararnamesi": 19,
  "Cumhurbaşkanı Kararı": 20,
  "Cumhurbaşkanlığı Yönetmeliği": 21,
  "Cumhurbaşkanlığı Genelgesi": 22,
}

interface CountsResponse {
  year: number
  [key: string]: number | string
}

export default function DocumentsChart() {
  const [data, setData] = useState<CountsResponse[]>([])
  const [config, setConfig] = useState<ChartConfig>({})
  const [stacked, setStacked] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selected, setSelected] = useState<{ year: number; type: string } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)

  const handleSelect = useCallback(async (year: number, type: string) => {
    const typeId = typeLabelToId[type]
    if (!typeId || !year) return
    try {
      const params = new URLSearchParams({
        year: String(year),
        mevzuat_tur: String(typeId),
      })
      const res = await fetch(
        `/api/documents/list?${params.toString()}`,
      )
      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`)
      }
      const docs: Document[] = await res.json()
      setDocuments(docs)
      setError(null)
    } catch (err) {
      console.error(err)
      setDocuments([])
      setError("Failed to fetch documents")
    }
    setSelected({ year, type })
  }, [])

  /* -------------------------------------------------------------------------- */
  /*                                   FETCH                                    */
  /* -------------------------------------------------------------------------- */
  useEffect(() => {
    fetch("/api/documents/counts")
      .then((res) => res.json())
      .then((raw: CountsResponse[]) => {
        const sorted = [...raw].sort((a, b) => a.year - b.year)
        setData(sorted)

        const typeSet = new Set<string>()
        sorted.forEach((row) => {
          Object.keys(row).forEach((k) => k !== "year" && typeSet.add(k))
        })
        const types = Array.from(typeSet)

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
        types.forEach((t, idx) => {
          cfg[t] = { label: t, color: palette[idx % palette.length] }
        })
        setConfig(cfg)
      })
  }, [])

  /* -------------------------------------------------------------------------- */
  /*                                 TOOLTIP                                    */
  /* -------------------------------------------------------------------------- */
  const renderTooltip = useMemo(() => {
    return (props: TooltipProps<number, string>) => {
      const { active, payload, label } = props
      if (!active || !payload || !payload.length) return null

      return (
        <div className="rounded-md bg-popover p-2 shadow-md text-sm">
          <div className="mb-1 font-medium">{label}</div>
          {payload
            .filter((p) => p && p.value !== 0)
            .map((p) => {
              const key = p.dataKey as string
              const color = config[key]?.color || p.color || "currentColor"
              const docLabel = config[key]?.label ?? key
              return (
                <div
                  key={key}
                  className="flex items-center gap-2 whitespace-nowrap cursor-pointer"
                  onClick={() => handleSelect(Number(label), docLabel)}
                >
                  <span
                    className="inline-block h-2 w-2 rounded-sm"
                    style={{ background: color }}
                  />
                  <span>
                    {docLabel}: {p.value}
                  </span>
                </div>
              )
            })}
        </div>
      )
    }
  }, [config, handleSelect])

  /* -------------------------------------------------------------------------- */
  /*                                  RENDER                                    */
  /* -------------------------------------------------------------------------- */
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Documents by Type over Time</CardTitle>
        <Button variant="outline" size="sm" onClick={() => setStacked((p) => !p)}>
          {stacked ? "Clustered" : "Stacked"}
        </Button>
      </CardHeader>

      <CardContent>
        <ChartContainer config={config}>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="year" tickLine={false} />
              <YAxis tickLine={false} />
              <Tooltip content={renderTooltip} />

              {Object.entries(config).map(([key, { color }]) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={color}
                  isAnimationActive={false}
                  {...(stacked ? { stackId: "docs" } : {})}
                  onClick={({ payload }: any) =>
                    handleSelect(Number(payload?.year), key)
                  }
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
      {selected && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>
              {selected.type} ({selected.year})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {error ? (
              <div>{error}</div>
            ) : documents.length ? (
              <ul className="list-disc pl-4">
                {documents.map((doc) => (
                  <li key={doc.id}>{doc.name}</li>
                ))}
              </ul>
            ) : (
              <div>No documents found.</div>
            )}
          </CardContent>
        </Card>
      )}
    </Card>
  )
}
