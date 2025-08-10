"use client"

import { useEffect, useState, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface VectorStore {
  name: string
  id: string
}

function SearchPageContent() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [vectorStores, setVectorStores] = useState<VectorStore[]>([])
  const searchParams = useSearchParams()

  useEffect(() => {
    async function fetchVectorStores() {
      try {
        const res = await fetch("/api/documents/vector-stores")
        const data = await res.json()
        setVectorStores(data || [])
      } catch (err) {
        console.error(err)
      }
    }
    fetchVectorStores()
  }, [])

  useEffect(() => {
    const q = searchParams.get("q")
    if (q) setQuery(q)
  }, [searchParams])

  useEffect(() => {
    const q = searchParams.get("q")
    if (!q || vectorStores.length === 0) return
    ;(async () => {
      setLoading(true)
      try {
        const responses = await Promise.all(
          vectorStores.map((vs) =>
            fetch(`/api/documents/vector-stores/${vs.id}/search`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query: q }),
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
  }, [searchParams, vectorStores])

  async function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!query || vectorStores.length === 0) return
    setLoading(true)
    try {
      const responses = await Promise.all(
        vectorStores.map((vs) =>
          fetch(`/api/documents/vector-stores/${vs.id}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
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
  }

  return (
    <div className="container max-w-2xl mx-auto py-10 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Semantic Search</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSearch} className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your query"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {results.length > 0 && (
        <div className="space-y-4">
          {results.map((r, i) => (
            <Card key={i}>
              <CardHeader>
                <CardTitle>{r?.metadata?.title || `Result ${i + 1}`}</CardTitle>
              </CardHeader>
              <CardContent>
                {r?.content?.[0]?.text || r?.snippet || ""}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchPageContent />
    </Suspense>
  )
}

