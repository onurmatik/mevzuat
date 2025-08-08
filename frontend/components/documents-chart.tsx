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
import { ChartContainer } from "@/components/ui/chart"
import { useDocumentsChart } from "@/components/documents-chart-context"

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
  const { config, visible, rangeOption, customRange, typeLabelToId } =
    useDocumentsChart()
  const [data, setData] = useState<CountRow[]>([])
  const [stacked, setStacked] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [selected, setSelected] = useState<{ date: string; type: string } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [interval, setInterval] = useState<"year" | "month" | "day">("year")

  const handleSelect = useCallback(
    async (date: string, type: string) => {
      const typeId = typeLabelToId[type]
      if (!typeId || !date) return
      try {
        const d = new Date(date)
        const params = new URLSearchParams({ type: String(typeId) })
        let label = ""
        if (interval === "day") {
          const ds = d.toISOString().split("T")[0]
          params.set("date", ds)
          label = ds
        } else if (interval === "month") {
          params.set("year", String(d.getFullYear()))
          params.set("month", String(d.getMonth() + 1))
          label = d.toLocaleString(undefined, { month: "long", year: "numeric" })
        } else {
          params.set("year", String(d.getFullYear()))
          label = String(d.getFullYear())
        }
        const res = await fetch(`/api/documents/list?${params.toString()}`)
        if (!res.ok) {
          throw new Error(`Request failed: ${res.status}`)
        }
        const docs: Document[] = await res.json()
        setDocuments(docs)
        setError(null)
        setSelected({ date: label, type })
      } catch (err) {
        console.error(err)
        setDocuments([])
        setError("Failed to fetch documents")
      }
    },
    [typeLabelToId, interval],
  )

  /* -------------------------------------------------------------------------- */
  /*                                   FETCH                                    */
  /* -------------------------------------------------------------------------- */
  useEffect(() => {
    async function loadCounts() {
      try {
        const today = new Date()
        const params = new URLSearchParams()
        let newInterval: "year" | "month" | "day" = "year"
        if (rangeOption === "all") {
          newInterval = "year"
        } else if (rangeOption === "thisYear") {
          newInterval = "month"
          params.set("start_date", `${today.getFullYear()}-01-01`)
          params.set("end_date", today.toISOString().split("T")[0])
        } else if (rangeOption === "lastYear") {
          newInterval = "month"
          const year = today.getFullYear() - 1
          params.set("start_date", `${year}-01-01`)
          params.set("end_date", `${year}-12-31`)
        } else if (rangeOption === "custom" && customRange?.from && customRange?.to) {
          newInterval = "day"
          params.set(
            "start_date",
            customRange.from.toISOString().split("T")[0],
          )
          params.set(
            "end_date",
            customRange.to.toISOString().split("T")[0],
          )
        } else {
          newInterval = "day"
          const past = new Date(today)
          past.setDate(past.getDate() - 30)
          params.set("start_date", past.toISOString().split("T")[0])
          params.set("end_date", today.toISOString().split("T")[0])
        }
        params.set("interval", newInterval)
        setInterval(newInterval)
        const countsRes = await fetch(
          `/api/documents/counts?${params.toString()}`,
        )
        const raw: RawCount[] = await countsRes.json()

        const allowed = new Set(Object.keys(typeLabelToId))
        const filtered = raw.filter((r) => allowed.has(r.type))

        const map = new Map<string, CountRow>()
        filtered.forEach(({ period, type, count }) => {
          const row = map.get(period) ?? { date: period }
          row[type] = count
          map.set(period, row)
        })

        const sorted = Array.from(map.values()).sort((a, b) =>
          a.date.localeCompare(b.date),
        )
        setData(sorted)
        setSelected(null)
      } catch (err) {
        console.error(err)
      }
    }
    if (Object.keys(typeLabelToId).length) {
      loadCounts()
    }
  }, [rangeOption, typeLabelToId, customRange])

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

      <CardContent>
        <ChartContainer config={config}>
          {data.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={data}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  tickFormatter={(value) => {
                    const d = new Date(value)
                    if (interval === "year") return String(d.getFullYear())
                    if (interval === "month")
                      return d.toLocaleDateString(undefined, {
                        month: "short",
                        year: "numeric",
                      })
                    return d.toLocaleDateString()
                  }}
                />
                <YAxis tickLine={false} />
                <Tooltip content={renderTooltip} />

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
