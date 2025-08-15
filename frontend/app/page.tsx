"use client"

import { useState, useCallback, Suspense } from "react"
import DocumentsChart from "@/components/documents-chart"
import SearchResults from "@/components/search-results"

export default function Home() {
  const [listResults, setListResults] = useState<any[]>([])
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({})
  const clearExternal = useCallback(() => setListResults([]), [])

  return (
    <main className="p-6">
      <DocumentsChart onDocuments={setListResults} typeCounts={typeCounts} />
      <Suspense fallback={null}>
        <SearchResults
          externalResults={listResults}
          clearExternal={clearExternal}
          onTypeCounts={setTypeCounts}
        />
      </Suspense>
    </main>
  )
}

