import React, { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Markdown from 'react-markdown';
import { ArrowLeft, Share2, Printer, Download, Clock, Hash, FileText, ArrowUpRight, BookOpen, Scale, Flag } from 'lucide-react';
import { DOC_TYPE_LABELS } from '../data/documentTypes'; // Keep labels for now, or fetch from API types? Labels are translation maps. api returns strings.
import { useLanguage } from '../store/language';
import { useAuth } from '../store/auth';
import { api, Document } from '../lib/api';
import { cn } from '../lib/utils';

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [relatedDocs, setRelatedDocs] = useState<Document[]>([]);
  const { isAuthenticated, user } = useAuth();
  const [flagging, setFlagging] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [showFlagConfirm, setShowFlagConfirm] = useState(false);

  const { t, language } = useLanguage();

  const summaryMarkdown = useMemo(() => {
    if (!doc?.summary) return '';
    return doc.summary.replace(/^\s*-\s+/gm, '- ');
  }, [doc?.summary]);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      try {
        const d = await api.getDocument(id);
        setDoc(d);

        const related = await api.searchDocuments(undefined, {
          related_to: d.uuid,
          limit: 3
        });
        setRelatedDocs(related.data.map(r => ({
          id: r.attributes.id || 0,
          uuid: r.attributes.uuid || '',
          title: r.attributes.title || r.filename,
          content: null,
          summary: r.attributes.summary ?? null,
          keywords: r.attributes.keywords ?? null,
          keywords_en: r.attributes.keywords_en ?? null,
          number: r.attributes.number ?? null,
          type: r.type,
          date: r.attributes.date || null
        })));
      } catch (e) {
        console.error("Failed to load doc", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const pushActionNotice = (message: string) => {
    setActionNotice(message);
    window.setTimeout(() => {
      setActionNotice((current) => (current === message ? null : current));
    }, 3000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleShare = async () => {
    const shareUrl = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({
          title: doc?.title,
          url: shareUrl,
        });
        return;
      }
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
        pushActionNotice("Link copied.");
        return;
      }
      window.prompt("Copy this link:", shareUrl);
    } catch (e) {
      console.error("Share failed", e);
      pushActionNotice("Share failed.");
    }
  };

  const confirmFlag = async () => {
    if (!doc || !isAuthenticated) return;
    setShowFlagConfirm(false);
    setFlagging(true);
    try {
      await api.flagDocument(doc.uuid);
      pushActionNotice("Document flagged. Thanks for the feedback.");
    } catch (e) {
      console.error("Flag failed", e);
      pushActionNotice("Failed to flag document.");
    } finally {
      setFlagging(false);
    }
  };



  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-background">Loading...</div>;
  }

  if (!doc) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="bg-muted inline-flex p-4 rounded-full mb-4">
            <FileText size={32} className="text-muted-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">Document Not Found</h1>
          <p className="text-muted-foreground mb-6">The document you requested could not be located.</p>
          <Link to="/" className="text-primary hover:underline font-medium">
            Return Home
          </Link>
        </div>
      </div>
    );
  }

  // Fallback for type label if not found in MOCK
  const typeKey = doc.type;
  const typeLabel = (DOC_TYPE_LABELS as any)[typeKey]?.[language] || doc.type;
  const docKeywords = (language === 'en' && doc.keywords_en && doc.keywords_en.length > 0)
    ? doc.keywords_en
    : (doc.keywords || []);
  const uniqueKeywords = Array.from(new Set(docKeywords)).filter(Boolean);
  const downloadUrl = doc.document_url || doc.original_document_url;

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Utility Bar */}
      <div className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link to="/search" className="text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-2 transition-colors">
            <ArrowLeft size={16} />
            {t('nav.search')}
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors"
              title="Print"
            >
              <Printer size={16} />
            </button>
            <button
              type="button"
              onClick={handleShare}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors"
              title="Share"
            >
              <Share2 size={16} />
            </button>
            {isAuthenticated && (
              <button
                type="button"
                onClick={() => setShowFlagConfirm((current) => !current)}
                disabled={flagging}
                className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                title="Flag as Problematic"
              >
                <Flag size={16} />
              </button>
            )}
            <div className="w-px h-4 bg-border mx-1"></div>
            {downloadUrl ? (
              <a
                href={downloadUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-medium rounded-md hover:bg-primary/90 transition-colors"
              >
                <Download size={14} />
                <span>Download PDF</span>
              </a>
            ) : (
              <button
                type="button"
                disabled
                className="flex items-center gap-2 px-3 py-1.5 bg-primary/50 text-primary-foreground/70 text-xs font-medium rounded-md cursor-not-allowed"
                title="PDF not available"
              >
                <Download size={14} />
                <span>Download PDF</span>
              </button>
            )}
            {actionNotice && (
              <span className="text-xs text-muted-foreground ml-2">{actionNotice}</span>
            )}
          </div>
        </div>
        {showFlagConfirm && (
          <div className="border-t border-border/60 bg-background/90">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-2 flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">
                Flag this document as problematic?
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowFlagConfirm(false)}
                  className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmFlag}
                  disabled={flagging}
                  className="text-xs font-medium text-destructive bg-destructive/10 hover:bg-destructive/20 px-2.5 py-1 rounded"
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">

          {/* Main Content */}
          <div className="lg:col-span-8">
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-4">
                <span className="inline-flex items-center rounded-md bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
                  {typeLabel}
                </span>
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground font-mono">
                  <Hash size={12} />
                  {doc.number || "-"}
                </span>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock size={12} /> {doc.date}
                </span>
              </div>

              <h1 className="sm:text-2xl font-bold text-foreground leading-tight mb-4">
                {doc.title}
              </h1>

              <div className="bg-muted/30 rounded-lg p-5 border border-border/50 relative group">
                {doc.summary ? (
                  <div className="text-lg text-muted-foreground italic leading-relaxed">
                    <Markdown
                      components={{
                        ul: ({ ...props }) => (
                          <ul className="list-disc pl-6 space-y-2" {...props} />
                        ),
                        li: ({ ...props }) => (
                          <li className="leading-relaxed" {...props} />
                        ),
                        p: ({ ...props }) => (
                          <p className="leading-relaxed" {...props} />
                        ),
                      }}
                    >
                      {summaryMarkdown}
                    </Markdown>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No summary available.</p>
                )}
              </div>
            </div>

            <article className="prose prose-slate dark:prose-invert max-w-none 
              prose-headings:font-semibold prose-headings:tracking-tight
              prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4
              prose-p:leading-7 prose-p:text-foreground/90
              prose-li:text-foreground/90
            ">
              <Markdown>{doc.content || "*No content available*"}</Markdown>
            </article>
          </div>

          {/* Sidebar Metadata */}
          <div className="lg:col-span-4">
            <div className="sticky top-24 space-y-6">

              {/* Related Documents Section (NEW) */}
              <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4 pb-2 border-b border-border">
                  {t('doc.related_docs')}
                </h3>

                <div className="space-y-4">
                  {relatedDocs.map(relatedDoc => (
                    <Link key={relatedDoc.id} to={`/document/${relatedDoc.id}`} className="block group">
                      <div className="flex gap-3">
                        <div className="mt-1 min-w-[20px]">
                          {/* Icon logic based on type */}
                          <BookOpen size={16} className="text-muted-foreground" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-snug">
                            {relatedDoc.title}
                          </h4>
                          <span className="text-[10px] text-muted-foreground mt-1 block">
                            {relatedDoc.date} • {relatedDoc.type}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                  {relatedDocs.length === 0 && <span className="text-xs text-muted-foreground">No related document found.</span>}
                </div>

                <div className="mt-5 pt-3 border-t border-border/50">
                  <Link
                    to={`/search?related_to=${id}`}
                    className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                  >
                    {t('doc.all_related')}
                    <ArrowUpRight size={12} />
                  </Link>
                </div>
              </div>

              {/* Related Topics */}
              <div className="rounded-lg border border-border bg-muted/20 p-5">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-3">{t('doc.topics')}</h4>
                <div className="flex flex-wrap gap-2">
                  {uniqueKeywords.length > 0 ? (
                    uniqueKeywords.map((keyword) => (
                      <Link
                        key={keyword}
                        to={`/search?q=${encodeURIComponent(keyword)}`}
                        className="px-2 py-1 bg-background border border-border rounded text-xs text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                      >
                        {keyword}
                      </Link>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">No keywords available.</span>
                  )}
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
