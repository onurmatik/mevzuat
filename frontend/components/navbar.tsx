"use client"

import Link from "next/link"
import { Github } from "lucide-react"

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center gap-4 px-4 bg-background border-b">
      <Link href="/" className="text-xl font-bold">
        Mevzuat.info
      </Link>
      <Link
        href="https://github.com/onurmatik/mevzuat/"
        target="_blank"
        rel="noopener noreferrer"
        className="ml-auto"
      >
        <Github className="h-6 w-6" />
      </Link>
    </nav>
  )
}
