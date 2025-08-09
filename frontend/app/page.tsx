import DocumentsChart from "@/components/documents-chart"
import SearchResults from "@/components/search-results"

export default function Home() {
  return (
    <main className="p-6">
      <DocumentsChart />
      <SearchResults />
    </main>
  )
}

