import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Menu, X, Globe, User as UserIcon, LogOut } from 'lucide-react';
import { cn } from '../lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../store/language';
import { useAuth } from '../store/auth';

export function Navbar() {
  const location = useLocation();
  const [isOpen, setIsOpen] = React.useState(false);
  const { language, setLanguage, t } = useLanguage();
  const { isAuthenticated, user, openAuthModal, logout } = useAuth();

  const navLinks = [
    { name: t('nav.home'), path: '/' },
    { name: t('nav.search'), path: '/search' },
    { name: t('nav.pricing'), path: '/pricing' },
    { name: t('nav.api'), path: '/api-docs' },
  ];

  const isActive = (path: string) => location.pathname === path;

  const toggleLang = () => {
    setLanguage(language === 'tr' ? 'en' : 'tr');
  };

  return (
    <nav className="bg-background border-b border-border sticky top-0 z-40 w-full">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2.5">
              <div className="bg-primary/10 p-1.5 rounded-md text-primary">
                <BookOpen size={20} strokeWidth={2.5} />
              </div>
              <span className="font-semibold text-lg tracking-tight text-foreground">Mevzuat.info</span>
            </Link>
            
            <div className="hidden md:flex items-center space-x-1">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.path}
                  className={cn(
                    "px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    isActive(link.path)
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  {link.name}
                </Link>
              ))}
            </div>
          </div>

          <div className="hidden md:flex items-center gap-4">
            <button 
              onClick={toggleLang}
              className="text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-1.5 px-2 py-1 rounded hover:bg-secondary/50 transition-colors"
            >
              <Globe size={16} />
              <span>{language.toUpperCase()}</span>
            </button>

            <div className="h-4 w-px bg-border"></div>

            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                 <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                      <UserIcon size={16} />
                    </div>
                    <span className="hidden lg:inline-block">{user?.email?.split('@')[0]}</span>
                 </div>
                 <button 
                   onClick={logout}
                   className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full transition-colors"
                   title="Logout"
                 >
                   <LogOut size={18} />
                 </button>
              </div>
            ) : (
              <button 
                onClick={openAuthModal}
                className="text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md transition-colors shadow-sm"
              >
                {t('nav.login')}
              </button>
            )}
          </div>
          
          <div className="flex md:hidden items-center gap-4">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-muted-foreground hover:text-foreground p-2"
            >
              {isOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-background border-b border-border overflow-hidden"
          >
            <div className="px-4 py-4 space-y-2">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.path}
                  onClick={() => setIsOpen(false)}
                  className={cn(
                    "block px-3 py-2 text-base font-medium rounded-md",
                    isActive(link.path)
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )}
                >
                  {link.name}
                </Link>
              ))}
              <div className="pt-4 border-t border-border mt-4 flex items-center justify-between">
                 <button 
                  onClick={toggleLang}
                  className="text-sm font-medium text-muted-foreground flex items-center gap-2"
                >
                  <Globe size={16} /> {language.toUpperCase()}
                </button>
                
                {isAuthenticated ? (
                  <button 
                    onClick={() => { logout(); setIsOpen(false); }}
                    className="text-sm font-medium text-destructive hover:bg-destructive/10 px-4 py-2 rounded-md flex items-center gap-2"
                  >
                    <LogOut size={16} /> Logout
                  </button>
                ) : (
                  <button 
                    onClick={() => { openAuthModal(); setIsOpen(false); }}
                    className="text-sm font-medium bg-primary text-primary-foreground px-4 py-2 rounded-md"
                  >
                    {t('nav.login')}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}