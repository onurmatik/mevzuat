import React from 'react';
import { Link } from 'react-router-dom';
import { Hash, Calendar, Bookmark, BookmarkCheck } from 'lucide-react';
import { Document } from '../lib/api';
import { DOC_TYPE_LABELS } from '../data/documentTypes';
import { cn } from '../lib/utils';
import { useLanguage } from '../store/language';

interface DocumentCardProps {
  doc: Document;
  onRelated?: (doc: Document) => void;
  showKeywords?: boolean;
  showSaveAction?: boolean;
  isSaving?: boolean;
  onToggleSave?: (doc: Document) => void;
}

export function DocumentCard({
  doc,
  onRelated,
  showKeywords = true,
  showSaveAction = false,
  isSaving = false,
  onToggleSave,
}: DocumentCardProps) {
  const { language, t } = useLanguage();
  const typeKey = doc.type;
  const typeLabel = (DOC_TYPE_LABELS as any)[typeKey]?.[language] || doc.type;
  const numberLabel = doc.number ?? '-';
  const displayKeywords =
    language === 'en' && doc.keywords_en && doc.keywords_en.length > 0
      ? doc.keywords_en
      : (doc.keywords || []);
  const isSaved = Boolean(doc.is_saved);
  const saveLabel = isSaved ? t('doc.remove_from_library') : t('doc.save_to_library');

  return (
    <Link to={`/document/${doc.uuid}`} className="block group h-full">
      <article className="bg-card h-full rounded-lg border border-border p-5 hover:border-ring/50 hover:shadow-sm transition-all duration-200 flex flex-col">
        <div className="flex justify-between items-start mb-4 gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground ring-1 ring-inset ring-gray-500/10">
              {typeLabel}
            </span>
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground font-mono">
              <Hash size={12} />
              {numberLabel}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center text-xs text-muted-foreground tabular-nums">
              <Calendar size={12} className="mr-1.5" />
              {doc.date}
            </div>
            {showSaveAction && (
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onToggleSave?.(doc);
                }}
                disabled={isSaving}
                title={saveLabel}
                aria-label={saveLabel}
                aria-pressed={isSaved}
                className={cn(
                  "inline-flex h-8 w-8 items-center justify-center rounded-md border border-border/60 transition-colors",
                  isSaved
                    ? "bg-primary/10 text-primary hover:bg-primary/15"
                    : "bg-background text-muted-foreground hover:text-foreground hover:bg-secondary/60",
                  isSaving && "opacity-60 cursor-wait"
                )}
              >
                {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
              </button>
            )}
          </div>
        </div>

        <h3 className="text-lg font-semibold text-foreground leading-snug mb-3 group-hover:text-primary transition-colors line-clamp-2">
          {doc.title}
        </h3>

        <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed mb-4 flex-1">
          {doc.summary}
        </p>

        {(showKeywords && displayKeywords.length > 0) || onRelated ? (
          <div className="mt-auto pt-2 flex flex-wrap items-center gap-1.5">
            {showKeywords && displayKeywords.slice(0, 6).map((keyword) => (
                <Link
                  key={keyword}
                  to={`/search?q=${encodeURIComponent(keyword)}`}
                  onClick={(event) => {
                    event.stopPropagation();
                  }}
                  className="text-[10px] uppercase tracking-wide text-muted-foreground border border-border/60 rounded px-1.5 py-0.5 bg-background hover:border-primary/50 hover:text-primary transition-colors"
                >
                  {keyword}
                </Link>
              ))}
            {onRelated && (
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onRelated(doc);
                }}
                className="text-[10px] font-medium text-primary/90 border border-primary/20 rounded px-2 py-0.5 bg-primary/5 hover:bg-primary/10 transition-colors"
              >
                Related to this
              </button>
            )}
          </div>
        ) : null}

      </article>
    </Link>
  );
}
