"use client"

import { Search, Calendar as CalendarIcon } from "lucide-react"
import {
  useDocumentsChart,
  RangeOption,
} from "@/components/documents-chart-context"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
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
    typeLabelToId,
  } = useDocumentsChart()
  const [query, setQuery] = useState("")
  const [commandOpen, setCommandOpen] = useState(false)
  const [vectorStores, setVectorStores] = useState<{ id: string; name: string }[]>([])
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setCommandOpen((o) => !o)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  useEffect(() => {
    async function fetchVectorStores() {
      try {
        const res = await fetch("/api/documents/vector-stores")
        const data = await res.json()
        const mapped = (data || []).map((d: any) => ({ id: d.uuid, name: d.name }))
        setVectorStores(mapped)
      } catch (err) {
        console.error(err)
      }
    }
    fetchVectorStores()
  }, [])

  // ---------------------------------------------------------------------------
  // Doc type visibility
  // ---------------------------------------------------------------------------

  function buildFilters() {
    const filters: any[] = []
    const typeIds = Object.entries(visible)
      .filter(([, v]) => v)
      .map(([label]) => typeLabelToId[label])
      .filter(Boolean)
    if (typeIds.length) {
      const typeFilters = typeIds.map((id) => ({
        type: "eq",
        key: "mevzuat_tur",
        value: id,
      }))
      filters.push(
        typeFilters.length === 1
          ? typeFilters[0]
          : { type: "or", filters: typeFilters },
      )
    }

    const today = new Date()
    let start: string | undefined
    let end: string | undefined
    if (rangeOption === "thisYear") {
      start = `${today.getFullYear()}-01-01`
      end = today.toISOString().split("T")[0]
    } else if (rangeOption === "lastYear") {
      const year = today.getFullYear() - 1
      start = `${year}-01-01`
      end = `${year}-12-31`
    } else if (rangeOption === "custom" && customRange?.from && customRange?.to) {
      start = customRange.from.toISOString().split("T")[0]
      end = customRange.to.toISOString().split("T")[0]
    } else if (rangeOption === "30days") {
      const past = new Date(today)
      past.setDate(past.getDate() - 30)
      start = past.toISOString().split("T")[0]
      end = today.toISOString().split("T")[0]
    }
    if (start)
      filters.push({ type: "gte", key: "date", value: start })
    if (end) filters.push({ type: "lte", key: "date", value: end })

    if (filters.length === 0) return undefined
    if (filters.length === 1) return filters[0]
    return { type: "and", filters }
  }

  async function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const q = query.trim()
    if (!q || vectorStores.length === 0) return
    setLoading(true)
    try {
      const filter = buildFilters()
      const responses = await Promise.all(
        vectorStores.map((vs) =>
          fetch(`/api/documents/vector-stores/${vs.id}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: q, filters: filter }),
          }).then((r) => r.json()),
        ),
      )
      const combined = responses.flatMap((r) => r?.data || [])
      setResults(combined)
      setCommandOpen(true)
    } catch (err) {
      console.error(err)
      setResults([])
    } finally {
      setLoading(false)
    }
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
          <PopoverContent className="w-56 p-0">
            <ScrollArea className="h-40 p-2">
              <div className="flex flex-col gap-2">
                {Object.entries(config).map(([key, { label, color }]) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 text-xs cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={visible[key] !== false}
                      onChange={() => toggleVisible(key)}
                      className="peer hidden"
                    />
                    <span className="flex h-4 w-4 items-center justify-center rounded-full border border-input">
                      <span className="hidden h-2 w-2 rounded-full bg-primary peer-checked:block" />
                    </span>
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: color }}
                    />
                    {label}
                  </label>
                ))}
              </div>
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
              className="h-8 w-full pl-8 pr-12"
            />
            <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              ⌘K
            </kbd>
          </div>
        </form>
      </nav>
      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
        <CommandInput placeholder="Search results" />
        <CommandList>
          {results.length > 0 ? (
            results.map((r, i) => (
              <CommandItem
                key={i}
                className="flex flex-col items-start gap-1"
              >
                <span className="font-medium">
                  {r?.metadata?.title || `Result ${i + 1}`}
                </span>
                <span className="text-xs text-muted-foreground">
                  {r?.content?.[0]?.text || r?.snippet || ""}
                </span>
              </CommandItem>
            ))
          ) : (
            <CommandEmpty>
              {loading ? "Searching..." : "No results found."}
            </CommandEmpty>
          )}
        </CommandList>
      </CommandDialog>
    </>
  )
}
