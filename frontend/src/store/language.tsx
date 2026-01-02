import React, { createContext, useContext, useState, ReactNode } from 'react';

type Language = 'tr' | 'en';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const translations: Record<string, Record<Language, string>> = {
  'nav.home': { tr: 'Ana Sayfa', en: 'Home' },
  'nav.search': { tr: 'Arama', en: 'Search' },
  'nav.pricing': { tr: 'Fiyatlandırma', en: 'Pricing' },
  'nav.login': { tr: 'Giriş Yap', en: 'Login' },
  'nav.continue_email': { tr: 'E-posta ile Devam Et', en: 'Continue with Email' },
  
  'hero.title': { tr: 'Mevzuatın Geleceği.', en: 'The Future of Legislation.' },
  'hero.subtitle': { tr: 'Türk hukuku için yapay zeka destekli, avant-garde bir arama motoru.', en: 'AI-powered, avant-garde search engine for Turkish law.' },
  'hero.search_placeholder': { tr: 'Kanun, kararname, yönetmelik ara...', en: 'Search laws, decrees, regulations...' },
  'hero.search_action': { tr: 'ARA', en: 'SEARCH' },
  
  'stats.title': { tr: 'VERİ AKIŞI', en: 'DATA FLOW' },
  'stats.subtitle': { tr: 'Son 6 ayın yasama hacmi', en: 'Legislative volume of last 6 months' },
  
  'recent.title': { tr: 'SON GİRİŞLER', en: 'LATEST ENTRIES' },
  'recent.view_all': { tr: 'TÜMÜNÜ GÖR', en: 'VIEW ALL' },
  
  'filter.title': { tr: 'FİLTRELER', en: 'FILTERS' },
  'filter.type': { tr: 'BELGE TÜRÜ', en: 'DOCUMENT TYPE' },
  'filter.date': { tr: 'TARİH ARALIĞI', en: 'DATE RANGE' },
  'filter.all': { tr: 'Tümü', en: 'All' },
  'filter.date_all': { tr: 'Tüm Zamanlar', en: 'All Time' },
  'filter.date_30': { tr: 'Son 30 Gün', en: 'Last 30 Days' },
  'filter.date_year': { tr: 'Son 1 Yıl', en: 'Last Year' },
  'filter.date_custom': { tr: 'Özel Aralık', en: 'Custom Range' },
  'filter.start_date': { tr: 'Başlangıç', en: 'Start Date' },
  'filter.end_date': { tr: 'Bitiş', en: 'End Date' },
  
  'doc.read': { tr: 'OKU', en: 'READ' },
  'doc.pdf': { tr: 'ORİJİNAL PDF', en: 'ORIGINAL PDF' },
  'doc.share': { tr: 'PAYLAŞ', en: 'SHARE' },
  'doc.print': { tr: 'YAZDIR', en: 'PRINT' },
  'doc.related_docs': { tr: 'İLGİLİ MEVZUAT', en: 'RELATED DOCUMENTS' },
  'doc.all_related': { tr: 'Tüm İlgili Belgeler', en: 'All Related Documents' },
  'doc.details': { tr: 'BELGE DETAYLARI', en: 'DOCUMENT DETAILS' },
  'doc.topics': { tr: 'İLGİLİ KONULAR', en: 'RELATED TOPICS' },
  
  'search.save': { tr: 'Aramayı Kaydet', en: 'Save Search' },
  'search.saved': { tr: 'Arama Kaydedildi', en: 'Search Saved' },
  'search.related_to': { tr: 'İlgili Mevzuat:', en: 'Related to:' },
  'search.clear_related': { tr: 'İlişkiyi Kaldır', en: 'Clear Relation' },
  
  'auth.modal_title': { tr: 'Giriş Yap', en: 'Login' },
  'auth.email_label': { tr: 'E-posta Adresi', en: 'Email Address' },
  'auth.submit': { tr: 'Sihirli Link Gönder', en: 'Send Magic Link' },
  'auth.sent': { tr: 'Link Gönderildi!', en: 'Link Sent!' },
  'auth.check_email': { tr: 'Lütfen e-posta kutunuzu kontrol edin.', en: 'Please check your inbox.' },
  
  'footer.rights': { tr: 'Tüm hakları saklıdır.', en: 'All rights reserved.' },
  'footer.desc': { tr: 'Mevzuat.info, modern hukuk profesyonelleri için tasarlanmıştır.', en: 'Mevzuat.info is designed for modern legal professionals.' },

  'nav.api': { tr: 'API', en: 'API' },
  'api.title': { tr: 'API Dokümantasyonu', en: 'API Documentation' },
  'api.subtitle': { tr: 'Verilerimize programatik olarak erişin.', en: 'Access our data programmatically.' },
  'api.intro': { tr: 'Aşağıdaki uç noktaları kullanarak Mevzuat.info veritabanına doğrudan erişebilirsiniz.', en: 'You can access our data programmatically through the available endpoints.' },
  'api.your_key': { tr: 'API Anahtarınız', en: 'Your API Key' },
  'api.upgrade_title': { tr: 'API Erişimi Edinin', en: 'Get API Access' },
  'api.upgrade_desc': { tr: 'API anahtarı almak ve sınırsız veri erişimi için Pro üyeliğe geçin.', en: 'Upgrade to Pro to get an API key and unlimited data access.' },
  'api.upgrade_btn': { tr: 'Pro\'ya Yükselt', en: 'Upgrade to Pro' },
  'api.pro_badge': { tr: 'PRO ÜYE', en: 'PRO MEMBER' },
  'api.copy': { tr: 'Kopyala', en: 'Copy' },
  'api.copied': { tr: 'Kopyalandı', en: 'Copied' }
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('tr');

  const t = (key: string) => {
    return translations[key]?.[language] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}