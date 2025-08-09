"use client"

import Link from "next/link"
import { Github, Calendar as CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Calendar } from "@/components/ui/calendar"
import {
  useDocumentsChart,
  RangeOption,
} from "@/components/documents-chart-context"
import { format } from "date-fns"

export default function Navbar() {
  const {
    config,
    visible,
    toggleVisible,
    rangeOption,
    setRangeOption,
    customRange,
    setCustomRange,
  } = useDocumentsChart()

  const activeSeries = Object.entries(visible)
    .filter(([, v]) => v)
    .map(([k]) => k)

  function handleSeriesChange(values: string[]) {
    Object.keys(config).forEach((key) => {
      const shouldBeVisible = values.includes(key)
      if ((visible[key] ?? true) !== shouldBeVisible) {
        toggleVisible(key)
      }
    })
  }

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center gap-4 px-4 bg-background border-b flex-wrap">
        <Link href="/" className="text-xl font-bold">
          Mevzuat.info
        </Link>

        <div className="flex items-center gap-4 flex-wrap">
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm">
                Series
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-56 p-0">
              <ScrollArea className="h-40 p-2">
                <ToggleGroup
                  type="multiple"
                  variant="outline"
                  className="flex flex-col gap-2"
                  value={activeSeries}
                  onValueChange={handleSeriesChange}
                >
                  {Object.entries(config).map(([key, { label, color }]) => (
                    <ToggleGroupItem
                      key={key}
                      value={key}
                      className="justify-start text-xs"
                      style=
                        {visible[key]
                          ? {
                              background: color,
                              color: "hsl(var(--background))",
                              borderColor: color,
                            }
                          : { borderColor: color }}
                    >
                      {label}
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
              </ScrollArea>
            </PopoverContent>
          </Popover>

          <div className="flex items-center gap-2">
            <ToggleGroup
              type="single"
              value={rangeOption === "custom" ? undefined : rangeOption}
              onValueChange={(val) => val && setRangeOption(val as RangeOption)}
              variant="outline"
              size="sm"
              className="flex"
            >
              {([
                ["all", "All"],
                ["thisYear", "This Year"],
                ["lastYear", "Last Year"],
                ["30days", "30 Days"],
              ] as [RangeOption, string][]).map(([key, label]) => (
                <ToggleGroupItem key={key} value={key}>
                  {label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>

            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={rangeOption === "custom" ? "default" : "outline"}
                  size="sm"
                  className="justify-start text-left font-normal w-[240px]"
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {customRange?.from && customRange?.to
                    ? `${format(customRange.from, "LLL dd, y")} - ${format(customRange.to, "LLL dd, y")}`
                    : "Custom"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="p-0" align="start">
                <Calendar
                  mode="range"
                  numberOfMonths={2}
                  selected={customRange}
                  onSelect={(range) => {
                    setCustomRange(range)
                    if (range?.from && range.to) {
                      setRangeOption("custom")
                    }
                  }}
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>

        <Link
          href="https://github.com/onurmatik/mevzuat/"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto"
        >
          <Github className="h-6 w-6" />
        </Link>
      </nav>
    </>
  )
}
