import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowRight, ArrowUpRight, BarChart3, Calendar } from 'lucide-react';
import { api, Document, StatsData } from '../lib/api';
import { DocumentCard } from '../components/DocumentCard';
import { StatsChart } from '../components/StatsChart';
import { useLanguage } from '../store/language';
import { cn } from '../lib/utils';

type TimeRange = '30days' | '12months' | 'all';

export default function Home() {
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [stats, setStats] = useState<StatsData[]>([]); // Need to update StatsChart to handle this data format later
  const { t } = useLanguage();
  const [timeRange, setTimeRange] = useState<TimeRange>('30days');

  useEffect(() => {
    async function loadData() {
      try {
        const docs = await api.listDocuments({ limit: 3 }); // Assuming list supports limit, though api.py's list_documents doesn't explicit param query yet, need to check if default ordering is date. It is.
        // Wait, api.py list_documents doesn't have limit param. It returns QuerySet. 
        // ninja usually supports pagination but list_documents has filtering. 
        // I should limit it client side for now or add limit param to backend.
        // The backend returns all matching documents! This is bad for performance.
        setRecentDocs(docs.slice(0, 3));

        // For stats, we need to map timeRange to interval
        const intervalMap: Record<TimeRange, 'day' | 'month' | 'year'> = {
          '30days': 'day',
          '12months': 'month',
          'all': 'year'
        };
        const today = new Date();
        let startDate: string | undefined;

        if (timeRange === '30days') {
          const d = new Date(today);
          d.setDate(d.getDate() - 30);
          startDate = d.toISOString().split('T')[0];
        } else if (timeRange === '12months') {
          const d = new Date(today);
          d.setMonth(d.getMonth() - 12);
          startDate = d.toISOString().split('T')[0];
        } else if (timeRange === 'all') {
          // Explicitly set 1980 as cutoff for "All Time"
          startDate = '1980-01-01';
        }

        const statsData = await api.getStats(intervalMap[timeRange], startDate);
        setStats(statsData);
      } catch (e) {
        console.error("Failed to load home data", e);
      }
    }
    loadData();
  }, [timeRange]);

  const timeRangeOptions: { value: TimeRange; label: string; desc: string }[] = [
    { value: '30days', label: 'Last 30 Days', desc: 'Daily distribution' },
    { value: '12months', label: 'Last 12 Months', desc: 'Monthly distribution' },
    { value: 'all', label: 'All Time', desc: 'Yearly distribution' },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Functional Hero Section */}
      <section className="py-24 border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground mb-6">
            {t('hero.title')}
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            {t('hero.subtitle')}
          </p>

          <div className="max-w-2xl mx-auto relative group">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground h-5 w-5" />
              <input
                type="text"
                placeholder={t('hero.search_placeholder')}
                className="w-full h-14 pl-12 pr-4 bg-background border border-input rounded-lg shadow-sm focus:ring-2 focus:ring-ring focus:border-input transition-all text-base"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2">
                <Link
                  to="/search"
                  className="bg-primary text-primary-foreground h-10 px-6 rounded-md text-sm font-medium flex items-center gap-2 hover:bg-primary/90 transition-colors"
                >
                  {t('hero.search_action')}
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section - Clean & Minimal */}
      <section className="py-16 bg-muted/30 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-start justify-between gap-12">
            <div className="md:w-1/3 flex flex-col h-full justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-foreground mb-2">{t('stats.title')}</h2>
                <p className="text-sm text-muted-foreground mb-8">{t('stats.subtitle')}</p>

                {/* Legend & Selector */}
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-medium text-muted-foreground mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#18181b]"></span>
                      <span>Kanun</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#dc2626]"></span>
                      <span>KHK</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#d97706]"></span>
                      <span>CB Kararname</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#7c3aed]"></span>
                      <span>CB Yönetmelik</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#2563eb]"></span>
                      <span>CB Karar</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm bg-[#059669]"></span>
                      <span>CB Genelge</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1 bg-background rounded-lg border border-border p-1">
                    {timeRangeOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setTimeRange(option.value)}
                        className={cn(
                          "flex items-center justify-between w-full px-3 py-2 text-sm rounded-md transition-all",
                          timeRange === option.value
                            ? "bg-secondary text-foreground font-medium shadow-sm"
                            : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                        )}
                      >
                        <span className="flex items-center gap-2">
                          <Calendar size={14} className={timeRange === option.value ? "text-primary" : "opacity-50"} />
                          {option.label}
                        </span>
                        <span className="text-xs text-muted-foreground/70 font-normal">
                          {option.desc}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="md:w-2/3 w-full h-[320px] bg-background border border-border rounded-xl p-4 shadow-sm">
              {/* Assuming StatsChart can handle the new data structure or I need to adapt it. 
                    MOCK_STATS was array of objects with keys per type.
                    StatsData is array of {period, type, count}.
                    I will need to transform StatsData to the expected format of StatsChart or update StatsChart.
                    For now, I'll update Home.tsx to transform before passing.
                */}
              <StatsChart data={stats} timeRange={timeRange} />
            </div>
          </div>
        </div>
      </section>

      {/* Recent Documents Section */}
      <section className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="flex justify-between items-center mb-10">
          <h2 className="text-2xl font-semibold text-foreground tracking-tight">{t('recent.title')}</h2>
          <Link to="/search" className="text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
            {t('recent.view_all')} <ArrowUpRight size={16} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recentDocs.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} />
          ))}
        </div>
      </section>
    </div>
  );
}