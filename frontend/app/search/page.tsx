"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const VECTOR_STORE_ID = process.env.NEXT_PUBLIC_VECTOR_STORE_ID ?? ""

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  async function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!query || !VECTOR_STORE_ID) return
    setLoading(true)
    try {
      const res = await fetch(`/api/documents/vector-stores/${VECTOR_STORE_ID}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      })
      const data = await res.json()
      setResults(data?.data || [])
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
