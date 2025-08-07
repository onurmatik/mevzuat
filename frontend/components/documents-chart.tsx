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
  Brush,
} from "recharts"
// 🔹 Use TooltipProps from the component’s type declarations so `payload` is recognised
import type { TooltipProps } from "recharts/types/component/Tooltip"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartConfig } from "@/components/ui/chart"

interface Document {
  id: number
  title: string
  type: number
  date?: string
}

interface RawCount {
  period: string
  type: string
  count: number
}

interface CountRow {
  date: string
  [key: string]: number | string
}

export default function DocumentsChart() {
  const [data, setData] = useState<CountRow[]>([])
  const [config, setConfig] = useState<ChartConfig>({})
  const [visible, setVisible] = useState<Record<string, boolean>>({})
  const [stacked, setStacked] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selected, setSelected] = useState<{ date: string; type: string } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [range, setRange] = useState<[number, number]>([0, 0])
  const [typeLabelToId, setTypeLabelToId] = useState<Record<string, number>>({})

  const handleToggle = (key: string) =>
    setVisible((p) => ({ ...p, [key]: !p[key] }))

  const handleSelect = useCallback(
    async (date: string, type: string) => {
      const typeId = typeLabelToId[type]
      if (!typeId || !date) return
      try {
        const params = new URLSearchParams({
          date,
          type: String(typeId),
        })
        const res = await fetch(`/api/documents/list?${params.toString()}`)
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
      setSelected({ date, type })
    },
    [typeLabelToId],
  )

  const displayed = useMemo(
    () => data.slice(range[0], range[1] + 1),
    [data, range],
  )

  const zoomIn = () => {
    const [start, end] = range
    const span = end - start + 1
    if (span <= 1) return
    const mid = Math.floor((start + end) / 2)
    const newSpan = Math.max(1, Math.floor(span / 2))
    let newStart = Math.max(0, mid - Math.floor(newSpan / 2))
    let newEnd = Math.min(data.length - 1, newStart + newSpan - 1)
    setRange([newStart, newEnd])
  }

  const zoomOut = () => {
    const [start, end] = range
    const span = end - start + 1
    const mid = Math.floor((start + end) / 2)
    const newSpan = Math.min(data.length, span * 2)
    let newStart = Math.max(0, mid - Math.floor(newSpan / 2))
    let newEnd = Math.min(data.length - 1, newStart + newSpan - 1)
    setRange([newStart, newEnd])
  }

  const panLeft = () => {
    const [start, end] = range
    const span = end - start
    const step = Math.max(1, Math.floor(span / 4))
    let newStart = Math.max(0, start - step)
    let newEnd = newStart + span
    setRange([newStart, newEnd])
  }

  const panRight = () => {
    const [start, end] = range
    const span = end - start
    const step = Math.max(1, Math.floor(span / 4))
    let newEnd = Math.min(data.length - 1, end + step)
    let newStart = newEnd - span
    setRange([newStart, newEnd])
  }

  /* -------------------------------------------------------------------------- */
  /*                                   FETCH                                    */
  /* -------------------------------------------------------------------------- */
  useEffect(() => {
    async function load() {
      try {
        const [countsRes, typesRes] = await Promise.all([
          fetch("/api/documents/counts"),
          fetch("/api/documents/types"),
        ])
        const raw: RawCount[] = await countsRes.json()
        const typeList: { id: number; label: string }[] = await typesRes.json()

        const typeMap: Record<string, number> = {}
        typeList.forEach(({ id, label }) => {
          typeMap[label] = id
        })
        setTypeLabelToId(typeMap)

        const map = new Map<string, CountRow>()
        raw.forEach(({ period, type, count }) => {
          const row = map.get(period) ?? { date: period }
          row[type] = count
          map.set(period, row)
        })

        const sorted = Array.from(map.values()).sort((a, b) =>
          a.date.localeCompare(b.date),
        )
        setData(sorted)

        // Avoid negative indices when the dataset is empty which would cause
        // NaN positioning values in Recharts components.
        const end = Math.max(sorted.length - 1, 0)
        const start = Math.max(end - 29, 0)
        setRange([start, end])

        const typeSet = new Set<string>()
        sorted.forEach((row) => {
          Object.keys(row).forEach((k) => k !== "date" && typeSet.add(k))
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
        const visibility: Record<string, boolean> = {}
        types.forEach((t, idx) => {
          cfg[t] = { label: t, color: palette[idx % palette.length] }
          visibility[t] = true
        })
        setConfig(cfg)
        setVisible(visibility)
      } catch (err) {
        console.error(err)
      }
    }
    load()
  }, [])

  /* -------------------------------------------------------------------------- */
  /*                                 TOOLTIP                                    */
  /* -------------------------------------------------------------------------- */
  const renderTooltip = useMemo(() => {
    return (
      props: TooltipProps<number, string> & {
        payload?: any[]
        label?: string | number
      }
    ) => {
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
                  onClick={() => handleSelect(String(label ?? ""), docLabel)}
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

      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-4">
          {Object.entries(config).map(([key, { label, color }]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={visible[key] ?? true}
                onChange={() => handleToggle(key)}
                className="rounded border-gray-300"
              />
              <span
                className="inline-block h-2 w-2 rounded-sm"
                style={{ background: color }}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={zoomIn}>
            Zoom In
          </Button>
          <Button variant="outline" size="sm" onClick={zoomOut}>
            Zoom Out
          </Button>
          <Button variant="outline" size="sm" onClick={panLeft}>
            ◀
          </Button>
          <Button variant="outline" size="sm" onClick={panRight}>
            ▶
          </Button>
        </div>
        <ChartContainer config={config}>
          {displayed.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={displayed}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis tickLine={false} />
                <Tooltip content={renderTooltip} />
                <Brush
                  dataKey="date"
                  startIndex={range[0]}
                  endIndex={range[1]}
                  onChange={(e) =>
                    e?.startIndex != null && e?.endIndex != null
                      ? setRange([e.startIndex, e.endIndex])
                      : null
                  }
                />

                {Object.entries(config)
                  .filter(([key]) => visible[key] !== false)
                  .map(([key, { color }]) => (
                    <Bar
                      key={key}
                      dataKey={key}
                      fill={color}
                      isAnimationActive={false}
                      {...(stacked ? { stackId: "docs" } : {})}
                      onClick={({ payload }: any) =>
                        handleSelect(payload?.date, key)
                      }
                    />
                  ))}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[350px] items-center justify-center text-sm text-muted-foreground">
              No data
            </div>
          )}
        </ChartContainer>
      </CardContent>
      {selected && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>
              {selected.type} ({selected.date})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {error ? (
              <div>{error}</div>
            ) : documents.length ? (
              <ul className="list-disc pl-4">
                {documents.map((doc) => (
                  <li key={doc.id}>{doc.title}</li>
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
