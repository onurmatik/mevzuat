"use client"

import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandItem,
} from "@/components/ui/command"
import { useDocumentsChart } from "@/components/documents-chart-context"
import { useState, useEffect } from "react"

export default function SearchNavbar() {
  const { visible, rangeOption, customRange, typeLabelToId } = useDocumentsChart()
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
      <nav className="sticky top-16 z-40 mt-16 flex items-center gap-2 px-4 h-16 bg-background border-b">
        <form onSubmit={onSearch} className="flex items-center gap-2 w-full">
          <div className="relative w-full max-w-md">
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
