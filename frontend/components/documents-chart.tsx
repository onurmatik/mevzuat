"use client"

import { useEffect, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartConfig, ChartTooltipContent } from "@/components/ui/chart"

interface CountsResponse {
  year: number
  [key: string]: number
}

export default function DocumentsChart() {
  const [data, setData] = useState<CountsResponse[]>([])
  const [config, setConfig] = useState<ChartConfig>({})

  useEffect(() => {
    fetch("/api/documents/counts")
      .then((res) => res.json())
      .then((data: CountsResponse[]) => {
        setData(data)
        const types = Object.keys(data[0] || {}).filter((k) => k !== "year")
        const colors = [
          "var(--chart-1)",
          "var(--chart-2)",
          "var(--chart-3)",
          "var(--chart-4)",
          "var(--chart-5)",
        ]
        const cfg: ChartConfig = {}
        types.forEach((t, idx) => {
          cfg[t] = { label: t, color: colors[idx % colors.length] }
        })
        setConfig(cfg)
      })
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents by Type over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config}>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="year" tickLine={false} />
              <Tooltip content={<ChartTooltipContent />} />
              {Object.keys(config).map((key) => (
                <Bar key={key} dataKey={key} fill={`var(--color-${key})`} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

