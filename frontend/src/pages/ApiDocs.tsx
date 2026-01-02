import React, { useState } from 'react';
import { Terminal, Copy, Check, Lock, Zap, Shield, ChevronRight } from 'lucide-react';
import { useAuth } from '../store/auth';
import { useLanguage } from '../store/language';

export default function ApiDocs() {
  const { user, isAuthenticated, upgradeToPro, openAuthModal } = useAuth();
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  const [isUpgrading, setIsUpgrading] = useState(false);

  const handleCopy = () => {
    if (user?.apiKey) {
      navigator.clipboard.writeText(user.apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleUpgrade = () => {
    if (!isAuthenticated) {
      openAuthModal();
      return;
    }
    
    setIsUpgrading(true);
    // Simulate network delay
    setTimeout(() => {
      upgradeToPro();
      setIsUpgrading(false);
    }, 1500);
  };

  const endpoints = [
    { method: 'GET', path: '/api/documents/types', desc: 'List all available document types.' },
    { method: 'GET', path: '/api/documents/counts', desc: 'Get counts of documents by type over a time interval.' },
    { method: 'GET', path: '/api/documents/list', desc: 'List documents with filters such as type, year, month, or date range.' },
    { method: 'GET', path: '/api/documents/search', desc: 'Search documents with optional filters like type and date range.' },
  ];

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-muted/30 border-b border-border py-12 lg:py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-primary/10 rounded-lg text-primary">
                  <Terminal size={24} />
                </div>
                <h1 className="text-3xl font-bold text-foreground tracking-tight">{t('api.title')}</h1>
              </div>
              <p className="text-lg text-muted-foreground max-w-2xl">
                {t('api.subtitle')}
              </p>
            </div>
            {user?.isPro && (
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-bold tracking-wide uppercase">
                <Zap size={14} fill="currentColor" />
                {t('api.pro_badge')}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          
          {/* Main Content */}
          <div className="lg:col-span-8 space-y-10">
            
            {/* Introduction */}
            <div>
              <p className="text-foreground/80 leading-relaxed text-lg">
                {t('api.intro')}
              </p>
            </div>

            {/* Endpoints */}
            <div className="space-y-6">
              {endpoints.map((ep, idx) => (
                <div key={idx} className="border border-border rounded-lg overflow-hidden bg-card shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-center border-b border-border/50 bg-muted/20 px-4 py-3">
                    <span className="font-mono text-sm font-bold text-primary px-2 py-0.5 bg-primary/10 rounded mr-3">
                      {ep.method}
                    </span>
                    <span className="font-mono text-sm text-foreground">
                      {ep.path}
                    </span>
                  </div>
                  <div className="p-4 text-sm text-muted-foreground">
                    {ep.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sidebar - API Key Section */}
          <div className="lg:col-span-4">
            <div className="sticky top-24">
              <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
                <div className="p-6">
                  <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Shield size={16} />
                    {t('api.your_key')}
                  </h3>

                  {user?.isPro ? (
                    // Pro View - Show API Key
                    <div className="space-y-4 animate-in fade-in zoom-in-95 duration-300">
                      <div className="relative group">
                        <div className="font-mono text-sm bg-muted p-3 rounded-md border border-border text-foreground break-all pr-10">
                          {user.apiKey}
                        </div>
                        <button 
                          onClick={handleCopy}
                          className="absolute right-2 top-2 p-1.5 text-muted-foreground hover:text-foreground hover:bg-background rounded-md transition-all"
                          title={t('api.copy')}
                        >
                          {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
                        </button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        This key grants unlimited access to all endpoints. Keep it secret.
                      </p>
                    </div>
                  ) : (
                    // Non-Pro View - Upgrade CTA
                    <div className="text-center space-y-5 py-2">
                      <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mx-auto text-muted-foreground">
                        <Lock size={24} />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground mb-1">{t('api.upgrade_title')}</h4>
                        <p className="text-sm text-muted-foreground">
                          {t('api.upgrade_desc')}
                        </p>
                      </div>
                      
                      <button 
                        onClick={handleUpgrade}
                        disabled={isUpgrading}
                        className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-2.5 rounded-lg font-medium hover:bg-primary/90 transition-all shadow-sm active:scale-95 disabled:opacity-70 disabled:pointer-events-none"
                      >
                        {isUpgrading ? (
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <>
                            <Zap size={16} fill="currentColor" />
                            {t('api.upgrade_btn')}
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Pro Features List (Decorational) */}
                {!user?.isPro && (
                  <div className="bg-muted/30 border-t border-border p-5 space-y-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Check size={14} className="text-green-500" />
                      <span>Unlimited requests</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Check size={14} className="text-green-500" />
                      <span>Full historical data</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Check size={14} className="text-green-500" />
                      <span>Priority support</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}