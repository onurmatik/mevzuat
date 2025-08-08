"use client"

import Link from "next/link"
import { Github } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useDocumentsChart, RangeOption } from "@/components/documents-chart-context"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function Navbar() {
  const {
    config,
    visible,
    toggleVisible,
    rangeOption,
    setRangeOption,
  } = useDocumentsChart()
  const [query, setQuery] = useState("")
  const router = useRouter()

  function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!query.trim()) return
    router.push(`/search?q=${encodeURIComponent(query.trim())}`)
    setQuery("")
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center gap-4 px-4 bg-background border-b flex-wrap">
      <Link href="/" className="text-xl font-bold">
        Mevzuat.info
      </Link>

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(config).map(([key, { label, color }]) => (
            <label key={key} className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={visible[key] ?? true}
                onChange={() => toggleVisible(key)}
                className="rounded border-gray-300"
              />
              <span
                className="inline-block h-2 w-2 rounded-sm"
                style={{ background: color }}
              />
              {label}
            </label>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {(
            [
              ["all", "All"],
              ["thisYear", "This Year"],
              ["lastYear", "Last Year"],
              ["30days", "30 Days"],
            ] as [RangeOption, string][]
          ).map(([key, label]) => (
            <Button
              key={key}
              variant={rangeOption === key ? "default" : "outline"}
              size="sm"
              onClick={() => setRangeOption(key)}
            >
              {label}
            </Button>
          ))}
        </div>
      </div>

      <form onSubmit={onSearch} className="ml-auto flex items-center gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search..."
          className="h-8 w-[180px]"
        />
      </form>

      <Link
        href="https://github.com/onurmatik/mevzuat/"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Github className="h-6 w-6" />
      </Link>
    </nav>
  )
}
