"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { useDocumentsChart } from "@/components/documents-chart-context"

interface VectorStore {
  id: string
  name: string
}

export default function SearchResults() {
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
    if (start)
      filters.push({ type: "gte", key: "date", value: start })
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

  if (!query) return null

  return (
    <div className="mt-6 space-y-4">
      {loading ? (
        <div>Searching...</div>
      ) : results.length > 0 ? (
        results.map((r, i) => {
          const title = r?.metadata?.title || `Result ${i + 1}`
          const date =
            r?.metadata?.resmi_gazete_tarihi || r?.metadata?.date || ""
          const fullSnippet =
            r?.content?.map((c: any) => c.text).join(" ") || r?.snippet || ""
          const shortSnippet =
            fullSnippet.length > 200
              ? fullSnippet.slice(0, 200) + "..."
              : fullSnippet

          const pdfUrl = buildPdfUrl(r?.metadata)

          return (
            <Dialog key={i}>
              <DialogTrigger asChild>
                <Card className="cursor-pointer">
                  <CardHeader>
                    <CardTitle>{title}</CardTitle>
                    {date && <CardDescription>{date}</CardDescription>}
                  </CardHeader>
                  <CardContent>{shortSnippet}</CardContent>
                </Card>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>{title}</DialogTitle>
                  {date && <DialogDescription>{date}</DialogDescription>}
                </DialogHeader>
                <div className="whitespace-pre-wrap">{fullSnippet}</div>
                {pdfUrl && (
                  <Button asChild className="mt-4">
                    <a href={pdfUrl} target="_blank" rel="noopener noreferrer">
                      Download PDF
                    </a>
                  </Button>
                )}
              </DialogContent>
            </Dialog>
          )
        })
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

