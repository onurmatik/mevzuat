"use client"

import { Search, Calendar as CalendarIcon } from "lucide-react"
import {
  useDocumentsChart,
  RangeOption,
} from "@/components/documents-chart-context"
import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover"
import { Checkbox } from "@/components/ui/checkbox"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { format } from "date-fns"

export default function SearchNavbar() {
  const {
    config,
    visible,
    toggleVisible,
    rangeOption,
    setRangeOption,
    customRange,
    setCustomRange,
  } = useDocumentsChart()
  const [query, setQuery] = useState("")
  const router = useRouter()
  const searchParams = useSearchParams()

  function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    const params = new URLSearchParams(searchParams.toString())
    params.set("q", q)
    router.push(`/?${params.toString()}`)
  }

  return (
    <>
      <nav className="sticky top-16 z-40 mt-16 flex items-center gap-4 px-4 py-2 bg-background border-b flex-wrap">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm">
              Types
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-56 p-2">
            <div className="flex flex-col gap-2">
              {Object.entries(config).map(([key, { label, color }]) => (
                <label
                  key={key}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <Checkbox
                    checked={visible[key] !== false}
                    onCheckedChange={() => toggleVisible(key)}
                  />
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: color }}
                  />
                  {label}
                </label>
              ))}
            </div>
          </PopoverContent>
        </Popover>

        <div className="flex items-center gap-2">
          <ToggleGroup
            type="single"
            value={rangeOption === "custom" ? undefined : rangeOption}
            onValueChange={(val) => {
              if (val) {
                setRangeOption(val as RangeOption)
                setCustomRange(undefined)
              }
            }}
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
              <ToggleGroupItem key={key} value={key} className="flex-none w-24">
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
            <PopoverContent className="w-auto p-0" align="start">
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

        <form
          onSubmit={onSearch}
          className="ml-auto flex items-center gap-2 w-full max-w-md"
        >
          <div className="relative w-full">
            <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search..."
              className="h-8 w-full pl-8 pr-2"
            />
          </div>
        </form>
      </nav>
    </>
  )
}
