import React from 'react';
import { useParams, Link } from 'react-router-dom';
import Markdown from 'react-markdown';
import { ArrowLeft, Share2, Printer, Download, Clock, Hash, FileText, ArrowUpRight, BookOpen, Scale } from 'lucide-react';
import { MOCK_DOCUMENTS, DOC_TYPE_LABELS } from '../data/mock';
import { useLanguage } from '../store/language';

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const doc = MOCK_DOCUMENTS.find((d) => d.id === id);
  const { t, language } = useLanguage();

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

  const typeLabel = DOC_TYPE_LABELS[doc.type][language];
  
  // Get related documents (mock implementation: get first 3 docs that are not the current one)
  const relatedDocs = MOCK_DOCUMENTS
    .filter(d => d.id !== id)
    .slice(0, 3);

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
              
              <div className="bg-muted/30 rounded-lg p-5 border border-border/50">
                <p className="text-lg text-muted-foreground italic leading-relaxed">
                  {doc.summary}
                </p>
              </div>
            </div>
            
            <article className="prose prose-slate dark:prose-invert max-w-none 
              prose-headings:font-semibold prose-headings:tracking-tight
              prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4
              prose-p:leading-7 prose-p:text-foreground/90
              prose-li:text-foreground/90
            ">
              <Markdown>{doc.content}</Markdown>
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
                      {doc.number}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground font-medium mb-1 uppercase">Publish Date</dt>
                    <dd className="font-medium text-foreground">{doc.date}</dd>
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
                           {relatedDoc.type === 'law' ? <Scale size={16} className="text-muted-foreground" /> : <BookOpen size={16} className="text-muted-foreground" />}
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-snug">
                            {relatedDoc.title}
                          </h4>
                          <span className="text-[10px] text-muted-foreground mt-1 block">
                            {relatedDoc.date} • {DOC_TYPE_LABELS[relatedDoc.type][language]}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
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