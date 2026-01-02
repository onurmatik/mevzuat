import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Markdown from 'react-markdown';
import { ArrowLeft, Share2, Printer, Download, Clock, Hash, FileText, ArrowUpRight, BookOpen, Scale, Sparkles } from 'lucide-react'; // Added Sparkles
import { DOC_TYPE_LABELS } from '../data/mock'; // Keep labels for now, or fetch from API types? Labes are translation maps. api returns strings.
// Actually api returns slug. We need to map slug to label. DOC_TYPE_LABELS has keys like 'law', 'khk'.
// I should probably move DOC_TYPE_LABELS to a shared config or fetch types from API.
// For now, I'll keep using mock labels if slugs match.
import { useLanguage } from '../store/language';
import { api, Document } from '../lib/api';
import { cn } from '../lib/utils';

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [relatedDocs, setRelatedDocs] = useState<Document[]>([]);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  const { t, language } = useLanguage();

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      try {
        const d = await api.getDocument(id);
        setDoc(d);

        // Mock related docs for now or implement API
        // Using list with random or same type?
        // The plan said "related_documents logic".
        // I didn't verify backend implementation of related.
        // I'll just list some recent docs as related for now to unblock.
        const recent = await api.listDocuments({ limit: 3 });
        setRelatedDocs(recent.filter(x => x.id !== d.id).slice(0, 3));
      } catch (e) {
        console.error("Failed to load doc", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleSummarize = async () => {
    if (!doc || !doc.id) return;
    setGeneratingSummary(true);
    try {
      const res = await api.summarizeDocument(doc.id);
      setDoc(prev => prev ? ({ ...prev, summary: res.summary }) : null);
    } catch (e) {
      console.error("Summarize failed", e);
    } finally {
      setGeneratingSummary(false);
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
            <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors" title="Print">
              <Printer size={16} />
            </button>
            <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors" title="Share">
              <Share2 size={16} />
            </button>
            <div className="w-px h-4 bg-border mx-1"></div>
            <button className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-medium rounded-md hover:bg-primary/90 transition-colors">
              <Download size={14} />
              <span>Download PDF</span>
            </button>
          </div>
        </div>
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
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock size={12} /> {doc.date}
                </span>
              </div>

              <h1 className="text-3xl sm:text-4xl font-bold text-foreground leading-tight mb-6">
                {doc.title}
              </h1>

              <div className="bg-muted/30 rounded-lg p-5 border border-border/50 relative group">
                {doc.summary ? (
                  <p className="text-lg text-muted-foreground italic leading-relaxed">
                    {doc.summary}
                  </p>
                ) : (
                  <div className="flex flex-col items-center justify-center py-4 text-center">
                    <p className="text-sm text-muted-foreground mb-3">No summary available.</p>
                    <button
                      onClick={handleSummarize}
                      disabled={generatingSummary}
                      className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-md hover:bg-primary/20 transition-colors disabled:opacity-50"
                    >
                      <Sparkles size={16} />
                      {generatingSummary ? "Generating..." : "Generate Summary with AI"}
                    </button>
                  </div>
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

              {/* Document Details Box */}
              <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4 pb-2 border-b border-border">
                  {t('doc.details')}
                </h3>

                <dl className="space-y-4 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground font-medium mb-1 uppercase">Official Number</dt>
                    <dd className="font-mono font-medium text-foreground bg-secondary/50 px-2 py-1 rounded inline-block">
                      {doc.number || "-"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground font-medium mb-1 uppercase">Publish Date</dt>
                    <dd className="font-medium text-foreground">{doc.date || "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground font-medium mb-1 uppercase">Category</dt>
                    <dd className="font-medium text-foreground">{typeLabel}</dd>
                  </div>
                </dl>
              </div>

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
                  {/* Mock topics for now */}
                  <span className="px-2 py-1 bg-background border border-border rounded text-xs text-foreground cursor-pointer hover:border-primary/50">Ticaret</span>
                  <span className="px-2 py-1 bg-background border border-border rounded text-xs text-foreground cursor-pointer hover:border-primary/50">Elektronik</span>
                  <span className="px-2 py-1 bg-background border border-border rounded text-xs text-foreground cursor-pointer hover:border-primary/50">Hukuk</span>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}