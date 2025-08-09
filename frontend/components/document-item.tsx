"use client"

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
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface DocumentItemProps {
  title: string
  date?: string
  type?: string
  snippet?: string
  fullSnippet?: string
  score?: number
  pdfUrl?: string | null
}

export default function DocumentItem({
  title,
  date,
  type,
  snippet,
  fullSnippet,
  score,
  pdfUrl,
}: DocumentItemProps) {
  const meta = [
    date,
    type,
    score !== undefined ? `Score: ${score.toFixed(2)}` : undefined,
  ]
    .filter(Boolean)
    .join(" • ")

  const card = (
    <Card className="cursor-pointer">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {meta && <CardDescription>{meta}</CardDescription>}
      </CardHeader>
      {snippet && <CardContent>{snippet}</CardContent>}
    </Card>
  )

  if (!fullSnippet && !pdfUrl) return card

  return (
    <Dialog>
      <DialogTrigger asChild>{card}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {meta && <DialogDescription>{meta}</DialogDescription>}
        </DialogHeader>
        {fullSnippet && (
          <div className="whitespace-pre-wrap">{fullSnippet}</div>
        )}
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
}

