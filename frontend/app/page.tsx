"use client"

import { useState, useCallback } from "react"
import DocumentsChart from "@/components/documents-chart"
import SearchResults from "@/components/search-results"

export default function Home() {
  const [listResults, setListResults] = useState<any[]>([])
  const clearExternal = useCallback(() => setListResults([]), [])

  return (
    <main className="p-6">
      <DocumentsChart onDocuments={setListResults} />
      <SearchResults externalResults={listResults} clearExternal={clearExternal} />
    </main>
  )
}

