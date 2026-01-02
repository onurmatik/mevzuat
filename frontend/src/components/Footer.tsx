import React from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../store/language';

export function Footer() {
  const { t, language } = useLanguage();

  const links = {
    home: { tr: 'Ana Sayfa', en: 'Home' },
    search: { tr: 'Arama', en: 'Search' },
    about: { tr: 'Hakkımızda', en: 'About' },
    contact: { tr: 'İletişim', en: 'Contact' },
    terms: { tr: 'Kullanım Koşulları', en: 'Terms of Use' },
    privacy: { tr: 'Gizlilik Politikası', en: 'Privacy Policy' },
    legal: { tr: 'Yasal Bildirim', en: 'Legal Notice' }
  };

  return (
    <footer className="bg-background border-t border-border py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="col-span-1 md:col-span-2">
            <h3 className="font-semibold text-lg text-foreground mb-4">Mevzuat.info</h3>
            <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
              {t('footer.desc')}
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold text-sm text-foreground mb-4">Platform</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/" className="hover:text-primary transition-colors">{links.home[language]}</Link></li>
              <li><Link to="/search" className="hover:text-primary transition-colors">{links.search[language]}</Link></li>
              <li><a href="#" className="hover:text-primary transition-colors">{links.about[language]}</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">{links.contact[language]}</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold text-sm text-foreground mb-4">Legal</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><a href="#" className="hover:text-primary transition-colors">{links.terms[language]}</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">{links.privacy[language]}</a></li>
              <li><a href="#" className="hover:text-primary transition-colors">{links.legal[language]}</a></li>
            </ul>
          </div>
        </div>
        
        <div className="pt-8 border-t border-border flex flex-col md:flex-row justify-between items-center text-xs text-muted-foreground">
          <div>
            &copy; {new Date().getFullYear()} Mevzuat.info. {t('footer.rights')}
          </div>
        </div>
      </div>
    </footer>
  );
}