"use client"

import { useEffect, useState, useMemo } from "react"
import { useSearchParams } from "next/navigation"
import { useDocumentsChart } from "@/components/documents-chart-context"
import DocumentItem from "@/components/document-item"

interface VectorStore {
  id: string
  name: string
}

interface ExternalDoc {
  id?: string | number
  title: string
  type?: number
  date?: string
  snippet?: string
  score?: number
}

export default function SearchResults({
  externalResults = [],
  clearExternal,
  onTypeCounts,
}: {
  externalResults?: ExternalDoc[]
  clearExternal: () => void
  onTypeCounts: (counts: Record<string, number>) => void
}) {
  const searchParams = useSearchParams()
  const query = searchParams.get("q")?.trim() || ""

  const { rangeOption, customRange, visible, typeLabelToId } = useDocumentsChart()

  const [vectorStores, setVectorStores] = useState<VectorStore[]>([])
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

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
    if (start) filters.push({ type: "gte", key: "date", value: start })
    if (end) filters.push({ type: "lte", key: "date", value: end })

    if (filters.length === 0) return undefined
    if (filters.length === 1) return filters[0]
    return { type: "and", filters }
  }

  useEffect(() => {
    if (!query || vectorStores.length === 0) return
    ;(async () => {
      setLoading(true)
      try {
        const filter = buildFilters()
        const responses = await Promise.all(
          vectorStores.map((vs) =>
            fetch(`/api/documents/vector-stores/${vs.id}/search`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query, filters: filter }),
            }).then((r) => r.json()),
          ),
        )
        const combined = responses.flatMap((r) => r?.data || [])
        setResults(combined)
      } catch (err) {
        console.error(err)
        setResults([])
      } finally {
        setLoading(false)
      }
    })()
  }, [query, vectorStores, rangeOption, customRange, visible])

  useEffect(() => {
    if (query) clearExternal()
  }, [query, clearExternal])

  const idToLabel = useMemo(() => {
    const map: Record<number, string> = {}
    Object.entries(typeLabelToId).forEach(([label, id]) => {
      map[id] = label
    })
    return map
  }, [typeLabelToId])

  const rawItems = (query ? results : externalResults).map((r, i) => {
    if (query) {
      const title = r?.metadata?.title || `Result ${i + 1}`
      const date = r?.metadata?.resmi_gazete_tarihi || r?.metadata?.date || ""
      const typeLabel = idToLabel[r?.metadata?.mevzuat_tur as number]
      const fullSnippet =
        r?.content?.map((c: any) => c.text).join(" ") || r?.snippet || ""
      const snippet =
        fullSnippet.length > 200 ? fullSnippet.slice(0, 200) + "..." : fullSnippet
      const pdfUrl = buildPdfUrl(r?.metadata)
      const score = r?.score
      return {
        title,
        date,
        type: typeLabel,
        snippet,
        fullSnippet,
        pdfUrl,
        score,
      }
    } else {
      const typeLabel = r.type !== undefined ? idToLabel[r.type] : undefined
      return {
        title: r.title,
        date: r.date,
        type: typeLabel,
        snippet: r.snippet,
        score: r.score,
      }
    }
  })

  const items = rawItems.filter(
    (item) => item.type === undefined || visible[item.type] !== false,
  )

  const counts = useMemo(() => {
    const map: Record<string, number> = {}
    items.forEach((item) => {
      if (item.type) map[item.type] = (map[item.type] ?? 0) + 1
    })
    return map
  }, [items])

  useEffect(() => {
    onTypeCounts(counts)
  }, [counts, onTypeCounts])

  if (!query && externalResults.length === 0) return null

  return (
    <div className="mt-6 space-y-4">
      {loading ? (
        <div>Searching...</div>
      ) : items.length > 0 ? (
        items.map((item, i) => <DocumentItem key={i} {...item} />)
      ) : (
        <div>No results found.</div>
      )}
    </div>
  )
}

function buildPdfUrl(meta: any): string | null {
  if (
    meta?.mevzuat_tur &&
    meta?.mevzuat_tertib &&
    meta?.mevzuat_no
  ) {
    return `https://www.mevzuat.gov.tr/MevzuatMetin/${meta.mevzuat_tur}.${meta.mevzuat_tertib}.${meta.mevzuat_no}.pdf`
  }
  if (meta?.pdf_url) return meta.pdf_url
  if (meta?.document_url) return meta.document_url
  return null
}

