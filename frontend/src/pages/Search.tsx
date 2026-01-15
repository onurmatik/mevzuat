import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, Filter, FileText, X, Bookmark, BookmarkCheck } from 'lucide-react';
import { DOC_TYPE_LABELS, DocType } from '../data/documentTypes';
import { DocumentCard } from '../components/DocumentCard';
import { StatsChart } from '../components/StatsChart';
import { useLanguage } from '../store/language';
import { useAuth } from '../store/auth';
import { api, Document, StatsData } from '../lib/api';
import { cn } from '../lib/utils';

const RELEVANCE_BAR_HEIGHTS = [3, 5, 7, 9, 11];

function RelevanceIcon({ level, className }: { level: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 20 12"
      className={cn("h-4 w-5", className)}
      aria-hidden="true"
      focusable="false"
    >
      {RELEVANCE_BAR_HEIGHTS.map((height, index) => {
        const isActive = index < level;
        return (
          <rect
            key={`bar-${index}`}
            x={index * 4}
            y={12 - height}
            width={3}
            height={height}
            rx={0.5}
            fill="currentColor"
            opacity={isActive ? 1 : 0.25}
          />
        );
      })}
    </svg>
  );
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const relatedToId = searchParams.get('related_to');

  const queryParam = searchParams.get('q');
  const [query, setQuery] = useState(queryParam ?? '');
  const [selectedType, setSelectedType] = useState<string | 'all'>('all');
  const [dateRange, setDateRange] = useState<'all' | 'last-30' | 'last-year' | 'custom'>('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [isSaved, setIsSaved] = useState(false);
  const [relatedDoc, setRelatedDoc] = useState<Document | null>(null);
  const [minScore, setMinScore] = useState(0.5);

  const { t, language } = useLanguage();
  const { isAuthenticated, openAuthModal } = useAuth();

  // Reset saved state when filters change
  useEffect(() => {
    setIsSaved(false);
  }, [query, selectedType, dateRange, relatedToId, minScore]);

  useEffect(() => {
    async function fetchRelated() {
      if (relatedToId) {
        try {
          const doc = await api.getDocument(relatedToId);
          setRelatedDoc(doc);
        } catch (e) {
          console.error("Failed to fetch related doc", e);
          setRelatedDoc(null);
        }
      } else {
        setRelatedDoc(null);
      }
    }
    fetchRelated();
  }, [relatedToId]);

  useEffect(() => {
    setQuery(queryParam ?? '');
  }, [queryParam]);

  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [statsData, setStatsData] = useState<StatsData[]>([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [savingIds, setSavingIds] = useState<Record<string, boolean>>({});
  const [savingSearch, setSavingSearch] = useState(false);

  const PAGE_SIZE = 10;
  const MAX_CHART_YEARS = 10;
  const RELEVANCE_OPTIONS = [
    { labelKey: 'filter.relevance_very_low', value: 0.1, level: 1 },
    { labelKey: 'filter.relevance_low', value: 0.3, level: 2 },
    { labelKey: 'filter.relevance_medium', value: 0.5, level: 3 },
    { labelKey: 'filter.relevance_high', value: 0.7, level: 4 },
    { labelKey: 'filter.relevance_very_high', value: 0.9, level: 5 },
  ];

  const { chartTimeRange, chartRangeStart, chartRangeEnd } = useMemo(() => {
    if (dateRange === 'last-30') {
      return { chartTimeRange: '30days' as const, chartRangeStart: undefined, chartRangeEnd: undefined };
    }
    if (dateRange === 'last-year') {
      return { chartTimeRange: '12months' as const, chartRangeStart: undefined, chartRangeEnd: undefined };
    }
    if (dateRange === 'custom' && (customStartDate || customEndDate)) {
      if (customStartDate && customEndDate) {
        const start = new Date(customStartDate);
        const end = new Date(customEndDate);
        if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
          const diffDays = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
          if (diffDays <= 31) {
            return { chartTimeRange: '30days' as const, chartRangeStart: customStartDate, chartRangeEnd: customEndDate };
          }
          if (diffDays <= 366) {
            return { chartTimeRange: '12months' as const, chartRangeStart: customStartDate, chartRangeEnd: customEndDate };
          }
        }
      }
      return { chartTimeRange: 'all' as const, chartRangeStart: customStartDate || undefined, chartRangeEnd: customEndDate || undefined };
    }
    const end = new Date();
    const startYear = end.getFullYear() - (MAX_CHART_YEARS - 1);
    const start = new Date(startYear, 0, 1);
    return {
      chartTimeRange: 'all' as const,
      chartRangeStart: start.toISOString().split('T')[0],
      chartRangeEnd: end.toISOString().split('T')[0]
    };
  }, [dateRange, customStartDate, customEndDate]);

  const statsTotal = useMemo(() => {
    return statsData.reduce((sum, item) => sum + item.count, 0);
  }, [statsData]);

  const totalResultsLabel = useMemo(() => {
    if (statsLoading) return '...';
    const locale = language === 'tr' ? 'tr-TR' : 'en-US';
    return new Intl.NumberFormat(locale).format(statsTotal);
  }, [statsLoading, statsTotal, language]);

  const handleRelatedFilter = useCallback((doc: Document) => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('related_to', doc.uuid);
    setSearchParams(newParams);
  }, [searchParams, setSearchParams]);

  const handleChartSegmentClick = useCallback((info: { period: string; type: string; timeRange: '30days' | '12months' | 'all' }) => {
    let start = '';
    let end = '';

    if (info.timeRange === '30days') {
      start = info.period;
      end = info.period;
    } else if (info.timeRange === '12months') {
      const [yearStr, monthStr] = info.period.split('-');
      const year = Number(yearStr);
      const month = Number(monthStr);
      if (!Number.isNaN(year) && !Number.isNaN(month)) {
        const startDate = new Date(year, month - 1, 1);
        const endDate = new Date(year, month, 0);
        start = startDate.toISOString().split('T')[0];
        end = endDate.toISOString().split('T')[0];
      }
    } else {
      const year = Number(info.period);
      if (!Number.isNaN(year)) {
        start = `${year}-01-01`;
        end = `${year}-12-31`;
      }
    }

    if (!start || !end) return;
    setSelectedType(info.type);
    setDateRange('custom');
    setCustomStartDate(start);
    setCustomEndDate(end);
  }, []);

  const buildFilters = () => {
    const filters: Record<string, any> = {};
    if (selectedType !== 'all') filters.type = selectedType;
    if (dateRange === 'last-30') {
      const d = new Date();
      d.setDate(d.getDate() - 30);
      filters.start_date = d.toISOString().split('T')[0];
    } else if (dateRange === 'last-year') {
      const d = new Date();
      d.setFullYear(d.getFullYear() - 1);
      filters.start_date = d.toISOString().split('T')[0];
    }
    if (dateRange === 'custom' && customStartDate) filters.start_date = customStartDate;
    if (dateRange === 'custom' && customEndDate) filters.end_date = customEndDate;

    if (relatedToId) {
      filters.related_to = relatedToId;
    }

    return filters;
  };

  useEffect(() => {
    let cancelled = false;

    async function loadStats() {
      setStatsLoading(true);
      try {
        const filters = buildFilters();
        const { start_date, end_date, ...restFilters } = filters;
        let statsStartDate = start_date;
        let statsEndDate = end_date;
        if (!statsStartDate && !statsEndDate && chartRangeStart && chartRangeEnd && dateRange === 'all') {
          statsStartDate = chartRangeStart;
          statsEndDate = chartRangeEnd;
        }
        const statsParams: Record<string, any> = { ...restFilters };
        if (query) statsParams.query = query;
        if (relatedToId) statsParams.related_to = relatedToId;
        if (relatedToId || query) {
          statsParams.min_score = minScore;
        }

        const interval =
          chartTimeRange === '30days' ? 'day' : chartTimeRange === '12months' ? 'month' : 'year';

        const data = await api.getStats(interval, statsStartDate, statsEndDate, statsParams);
        if (!cancelled) {
          setStatsData(data);
        }
      } catch (e) {
        console.error("Failed to load stats", e);
        if (!cancelled) {
          setStatsData([]);
        }
      } finally {
        if (!cancelled) {
          setStatsLoading(false);
        }
      }
    }

    loadStats();
    return () => {
      cancelled = true;
    };
  }, [query, selectedType, dateRange, customStartDate, customEndDate, relatedToId, chartTimeRange, chartRangeStart, chartRangeEnd, minScore]);

  useEffect(() => {
    setOffset(0);
    setDocs([]);
    setHasMore(false);
    setLoadingMore(false);
  }, [query, selectedType, dateRange, customStartDate, customEndDate, relatedToId, minScore]);

  useEffect(() => {
    let cancelled = false;

    async function doSearch() {
      const shouldSearch = Boolean(query) || Boolean(relatedToId);
      if (offset === 0) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }
      try {
        const filters = buildFilters();
        let results: Document[] = [];
        let more = false;

        if (shouldSearch) {
          const response = await api.searchDocuments(query || undefined, {
            ...filters,
            limit: PAGE_SIZE,
            offset,
            min_score: minScore
          });
          results = response.data.map(r => ({
            id: r.attributes.id || 0,
            uuid: r.attributes.uuid || '',
            title: r.attributes.title || r.filename,
            content: null,
            summary: r.attributes.summary ?? null,
            keywords: r.attributes.keywords ?? null,
            keywords_en: r.attributes.keywords_en ?? null,
            number: r.attributes.number ?? null,
            type: r.type,
            date: r.attributes.date || null,
            is_saved: r.is_saved ?? false
          }));
          more = response.has_more;
        } else {
          results = await api.listDocuments({
            ...filters,
            limit: PAGE_SIZE,
            offset
          });
          more = results.length === PAGE_SIZE;
        }

        if (cancelled) return;
        if (offset === 0) {
          setDocs(results);
        } else {
          setDocs(prev => [...prev, ...results]);
        }
        setHasMore(more);
      } catch (e) {
        console.error("Search failed", e);
      } finally {
        if (cancelled) return;
        if (offset === 0) {
          setLoading(false);
        } else {
          setLoadingMore(false);
        }
      }
    }

    doSearch();
    return () => {
      cancelled = true;
    };
  }, [query, selectedType, dateRange, customStartDate, customEndDate, relatedToId, minScore, offset]);

  const filteredDocs = docs; // Using state directly


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

  const handleSaveSearch = async () => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    setSavingSearch(true);
    try {
      const filters = {
        ...buildFilters(),
        date_range: dateRange,
        custom_start_date: customStartDate || null,
        custom_end_date: customEndDate || null,
        min_score: minScore,
      };
      await api.saveSearch({
        query: query.trim() || null,
        filters
      });
      setIsSaved(true);
    } catch (e) {
      console.error("Failed to save search", e);
    } finally {
      setSavingSearch(false);
    }
  };

  const handleToggleSave = async (doc: Document) => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    const nextSaved = !doc.is_saved;
    setSavingIds((prev) => ({ ...prev, [doc.uuid]: true }));
    try {
      if (nextSaved) {
        await api.saveDocument(doc.uuid);
      } else {
        await api.unsaveDocument(doc.uuid);
      }
      setDocs((prev) => prev.map((item) => (
        item.uuid === doc.uuid ? { ...item, is_saved: nextSaved } : item
      )));
    } catch (e) {
      console.error("Failed to toggle saved state", e);
    } finally {
      setSavingIds((prev) => {
        const next = { ...prev };
        delete next[doc.uuid];
        return next;
      });
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

                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase text-muted-foreground font-semibold">
                          Result Distribution
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {statsLoading ? '...' : statsTotal}
                        </span>
                      </div>
                      <div className="h-40 bg-background p-2">
                        {statsLoading ? (
                          <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
                            Loading...
                          </div>
                        ) : statsData.length > 0 ? (
                          <StatsChart
                            timeRange={chartTimeRange}
                            data={statsData}
                            rangeStart={chartRangeStart}
                            rangeEnd={chartRangeEnd}
                            onSegmentClick={handleChartSegmentClick}
                          />
                        ) : (
                          <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
                            No results to chart
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Relevance Filter */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-3 block uppercase tracking-wider">
                      {t('filter.relevance')}
                    </label>
                    <div className="flex items-center gap-2">
                      {RELEVANCE_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => setMinScore(option.value)}
                          className={cn(
                            "flex h-8 w-9 items-center justify-center rounded-md border border-transparent transition-colors",
                            minScore === option.value
                              ? "bg-primary text-primary-foreground"
                              : "bg-secondary/30 text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                          )}
                          type="button"
                          title={t(option.labelKey)}
                          aria-label={t(option.labelKey)}
                        >
                          <RelevanceIcon level={option.level} />
                        </button>
                      ))}
                    </div>
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
                <div className="bg-primary/5 border border-primary/20 rounded-md px-4 py-3 flex flex-col gap-3 animate-in fade-in slide-in-from-top-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 text-primary">
                        <Filter size={16} />
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-primary uppercase tracking-wide block mb-0.5">
                          {t('search.related_to')}
                        </span>
                        <p className="text-sm font-medium text-foreground">
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

                </div>
              )}
            </div>

            <div className="flex items-center justify-between mb-6 pb-2 border-b border-border/50">
              <h2 className="text-sm font-medium text-muted-foreground">
                Showing {filteredDocs.length} / {totalResultsLabel} results
              </h2>

              <button
                onClick={handleSaveSearch}
                disabled={isSaved || savingSearch}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${isSaved
                  ? 'bg-green-500/10 text-green-600 cursor-default'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
              >
                {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                {isSaved ? t('search.saved') : t('search.save')}
              </button>
            </div>

            {loading ? (
              <div
                className="text-center py-24 bg-muted/20 rounded-lg border border-dashed border-border"
                role="status"
                aria-live="polite"
              >
                <div className="h-10 w-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin mx-auto mb-3" />
                <p className="text-sm font-medium text-muted-foreground">{t('search.loading')}</p>
              </div>
            ) : filteredDocs.length > 0 ? (
              <div className="flex flex-col gap-4">
                {filteredDocs.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    onRelated={handleRelatedFilter}
                    showSaveAction
                    isSaving={Boolean(savingIds[doc.uuid])}
                    onToggleSave={handleToggleSave}
                  />
                ))}
                {hasMore && (
                  <div className="flex justify-center pt-4">
                    <button
                      onClick={() => setOffset(prev => prev + PAGE_SIZE)}
                      disabled={loadingMore}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${loadingMore
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                        }`}
                    >
                      {loadingMore ? 'Loading...' : 'Load more'}
                    </button>
                  </div>
                )}
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
                    setMinScore(0.5);
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
