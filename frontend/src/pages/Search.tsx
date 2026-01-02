import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, Filter, Calendar, FileText, X, Bookmark, BookmarkCheck } from 'lucide-react';
import { MOCK_DOCUMENTS, DocType, DOC_TYPE_LABELS } from '../data/mock';
import { DocumentCard } from '../components/DocumentCard';
import { useLanguage } from '../store/language';
import { useAuth } from '../store/auth';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const relatedToId = searchParams.get('related_to');
  
  const [query, setQuery] = useState('');
  const [selectedType, setSelectedType] = useState<DocType | 'all'>('all');
  const [dateRange, setDateRange] = useState<'all' | 'last-30' | 'last-year' | 'custom'>('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  
  const { t, language } = useLanguage();
  const { isAuthenticated, openAuthModal } = useAuth();

  // Reset saved state when filters change
  useEffect(() => {
    setIsSaved(false);
  }, [query, selectedType, dateRange, relatedToId]);

  const relatedDoc = useMemo(() => {
    return relatedToId ? MOCK_DOCUMENTS.find(d => d.id === relatedToId) : null;
  }, [relatedToId]);

  const filteredDocs = useMemo(() => {
    return MOCK_DOCUMENTS.filter((doc) => {
      // Related To Filter (Mock logic: exclude the doc itself, matching some logic?)
      // For demo, if relatedToId is present, we filter out the doc itself and maybe 
      // check if it has same type or some other property. 
      // Let's just exclude the ID itself and pretend others are related.
      if (relatedToId && doc.id === relatedToId) return false;

      // Text Search
      const matchesQuery = doc.title.toLowerCase().includes(query.toLowerCase()) || 
                           doc.summary.toLowerCase().includes(query.toLowerCase());
      
      // Type Filter
      const matchesType = selectedType === 'all' || doc.type === selectedType;
      
      // Date Filter
      let matchesDate = true;
      const docDate = new Date(doc.date);
      const now = new Date();
      
      if (dateRange === 'last-30') {
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(now.getDate() - 30);
        matchesDate = docDate >= thirtyDaysAgo;
      } else if (dateRange === 'last-year') {
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(now.getFullYear() - 1);
        matchesDate = docDate >= oneYearAgo;
      } else if (dateRange === 'custom') {
        if (customStartDate && customEndDate) {
           const start = new Date(customStartDate);
           const end = new Date(customEndDate);
           matchesDate = docDate >= start && docDate <= end;
        }
      }

      return matchesQuery && matchesType && matchesDate;
    });
  }, [query, selectedType, dateRange, customStartDate, customEndDate, relatedToId]);

  const dateOptions = [
    { value: 'all', labelKey: 'filter.date_all' },
    { value: 'last-30', labelKey: 'filter.date_30' },
    { value: 'last-year', labelKey: 'filter.date_year' },
    { value: 'custom', labelKey: 'filter.date_custom' },
  ];

  const clearRelatedFilter = () => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete('related_to');
    setSearchParams(newParams);
  };

  const handleSaveSearch = () => {
    if (isAuthenticated) {
      setIsSaved(true);
      // In a real app, API call to save search
    } else {
      openAuthModal();
    }
  };

  return (
    <div className="min-h-screen bg-background pt-8 pb-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Sidebar Filters */}
          <aside className="w-full lg:w-64 flex-shrink-0">
            <div className="sticky top-24 space-y-8">
              <div>
                <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Filter size={14} /> {t('filter.title')}
                </h3>
                
                <div className="space-y-8">
                  {/* Document Type Filter */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-3 block uppercase tracking-wider">
                      {t('filter.type')}
                    </label>
                    <div className="space-y-1">
                      <label className="flex items-center gap-2.5 px-2 py-1.5 -mx-2 rounded-md hover:bg-secondary/50 cursor-pointer transition-colors">
                        <input
                          type="radio"
                          name="docType"
                          value="all"
                          checked={selectedType === 'all'}
                          onChange={(e) => setSelectedType(e.target.value as any)}
                          className="w-4 h-4 text-primary border-muted-foreground/30 focus:ring-primary focus:ring-offset-0 rounded-full"
                        />
                        <span className={`text-sm ${selectedType === 'all' ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                          {t('filter.all')}
                        </span>
                      </label>

                      {(Object.keys(DOC_TYPE_LABELS) as DocType[]).map((type) => (
                        <label key={type} className="flex items-center gap-2.5 px-2 py-1.5 -mx-2 rounded-md hover:bg-secondary/50 cursor-pointer transition-colors">
                          <input
                            type="radio"
                            name="docType"
                            value={type}
                            checked={selectedType === type}
                            onChange={(e) => setSelectedType(e.target.value as any)}
                            className="w-4 h-4 text-primary border-muted-foreground/30 focus:ring-primary focus:ring-offset-0 rounded-full"
                          />
                          <span className={`text-sm ${selectedType === type ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                            {DOC_TYPE_LABELS[type][language]}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Date Range Filter */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-3 block uppercase tracking-wider">
                       {t('filter.date')}
                    </label>
                    <div className="space-y-1">
                      {dateOptions.map((option) => (
                        <label key={option.value} className="flex items-center gap-2.5 px-2 py-1.5 -mx-2 rounded-md hover:bg-secondary/50 cursor-pointer transition-colors">
                          <input
                            type="radio"
                            name="dateRange"
                            value={option.value}
                            checked={dateRange === option.value}
                            onChange={(e) => setDateRange(e.target.value as any)}
                            className="w-4 h-4 text-primary border-muted-foreground/30 focus:ring-primary focus:ring-offset-0 rounded-full"
                          />
                          <span className={`text-sm ${dateRange === option.value ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                            {t(option.labelKey)}
                          </span>
                        </label>
                      ))}
                    </div>

                    {dateRange === 'custom' && (
                      <div className="mt-3 p-3 bg-secondary/30 rounded-md border border-border/50 space-y-3 animate-in fade-in slide-in-from-top-1">
                        <div>
                           <label className="text-[10px] uppercase text-muted-foreground font-semibold mb-1 block">
                             {t('filter.start_date')}
                           </label>
                           <input 
                             type="date" 
                             className="w-full bg-background border border-input rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                             value={customStartDate}
                             onChange={(e) => setCustomStartDate(e.target.value)}
                           />
                        </div>
                        <div>
                           <label className="text-[10px] uppercase text-muted-foreground font-semibold mb-1 block">
                             {t('filter.end_date')}
                           </label>
                           <input 
                             type="date" 
                             className="w-full bg-background border border-input rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                             value={customEndDate}
                             onChange={(e) => setCustomEndDate(e.target.value)}
                           />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1">
            <div className="flex flex-col gap-4 mb-6">
              <div className="relative w-full">
                <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground h-5 w-5" />
                <input
                  type="text"
                  className="w-full h-12 pl-12 pr-4 bg-background border border-input rounded-lg text-base shadow-sm focus:ring-2 focus:ring-ring focus:border-input transition-all placeholder:text-muted-foreground"
                  placeholder={t('hero.search_placeholder')}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>

              {relatedDoc && (
                <div className="bg-primary/5 border border-primary/20 rounded-md px-4 py-3 flex items-start justify-between gap-4 animate-in fade-in slide-in-from-top-2">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 text-primary">
                      <Filter size={16} />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-primary uppercase tracking-wide block mb-0.5">
                        {t('search.related_to')}
                      </span>
                      <p className="text-sm font-medium text-foreground line-clamp-1">
                         {relatedDoc.title}
                      </p>
                    </div>
                  </div>
                  <button 
                    onClick={clearRelatedFilter}
                    className="text-muted-foreground hover:text-foreground hover:bg-background/50 p-1 rounded transition-colors"
                    title={t('search.clear_related')}
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between mb-6 pb-2 border-b border-border/50">
              <h2 className="text-sm font-medium text-muted-foreground">
                Showing {filteredDocs.length} results
              </h2>
              
              <button 
                onClick={handleSaveSearch}
                disabled={isSaved}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isSaved 
                    ? 'bg-green-500/10 text-green-600 cursor-default' 
                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                }`}
              >
                {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                {isSaved ? t('search.saved') : t('search.save')}
              </button>
            </div>

            {filteredDocs.length > 0 ? (
              <div className="flex flex-col gap-4">
                {filteredDocs.map((doc) => (
                  <DocumentCard key={doc.id} doc={doc} />
                ))}
              </div>
            ) : (
              <div className="text-center py-24 bg-muted/20 rounded-lg border border-dashed border-border">
                <FileText className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-foreground mb-1">No documents found</h3>
                <p className="text-sm text-muted-foreground mb-4">Try adjusting your search or filters.</p>
                <button 
                  onClick={() => {
                    setQuery(''); 
                    setSelectedType('all'); 
                    setDateRange('all');
                    clearRelatedFilter();
                  }}
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}