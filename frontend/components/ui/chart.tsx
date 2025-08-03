import * as React from "react"
import { TooltipProps } from "recharts"

import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"

export type ChartConfig = Record<string, { label: string; color: string }>

interface ChartContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  config: ChartConfig
}

export function ChartContainer({ config, children, className, ...props }: ChartContainerProps) {
  const style = Object.fromEntries(
    Object.entries(config).map(([key, value]) => [`--color-${key}`, value.color])
  )

  return (
    <div
      className={cn("w-full h-[350px]", className)}
      style={style as React.CSSProperties}
      {...props}
    >
      {children}
    </div>
  )
}

export function ChartTooltipContent({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const { name, value, color } = payload[0]
  return (
    <Card>
      <CardContent className="p-2 text-sm" style={{ color }}>
        {name}: {value}
      </CardContent>
    </Card>
  )
}

