import React from 'react';
import { Link } from 'react-router-dom';
import { Hash, Calendar, FileText } from 'lucide-react';
import { Document } from '../lib/api';
import { DOC_TYPE_LABELS } from '../data/mock';
import { cn, mapSlugToDocType } from '../lib/utils';
import { useLanguage } from '../store/language';

interface DocumentCardProps {
  doc: Document;
}

export function DocumentCard({ doc }: DocumentCardProps) {
  const { language } = useLanguage();
  const typeKey = mapSlugToDocType(doc.type);
  const typeLabel = (DOC_TYPE_LABELS as any)[typeKey]?.[language] || doc.type;

  return (
    <Link to={`/document/${doc.id}`} className="block group h-full">
      <article className="bg-card h-full rounded-lg border border-border p-5 hover:border-ring/50 hover:shadow-sm transition-all duration-200 flex flex-col">
        <div className="flex justify-between items-start mb-4">
          <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground ring-1 ring-inset ring-gray-500/10">
            {typeLabel}
          </span>
          <div className="flex items-center text-xs text-muted-foreground tabular-nums">
            <Calendar size={12} className="mr-1.5" />
            {doc.date}
          </div>
        </div>

        <h3 className="text-lg font-semibold text-foreground leading-snug mb-3 group-hover:text-primary transition-colors line-clamp-2">
          {doc.title}
        </h3>

        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4 pb-4 border-b border-border/50 w-full font-mono">
          <Hash size={12} />
          <span>{doc.number}</span>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed mb-4 flex-1">
          {doc.summary}
        </p>

        <div className="mt-auto pt-2">
          <span className="text-sm font-medium text-primary flex items-center gap-1 group-hover:underline underline-offset-4">
            Review Document
          </span>
        </div>
      </article>
    </Link>
  );
}