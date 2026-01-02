import React, { useLayoutEffect } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { AuthModal } from './components/AuthModal';
import Home from './pages/Home';
import SearchPage from './pages/Search';
import DocumentDetail from './pages/DocumentDetail';
import ApiDocs from './pages/ApiDocs';
import { LanguageProvider } from './store/language';
import { AuthProvider } from './store/auth';

// Scroll to top on route change
function ScrollToTop() {
  const { pathname } = useLocation();
  
  useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  
  return null;
}

function Layout() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex flex-col">
      <Navbar />
      <main className="flex-grow w-full">
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/document/:id" element={<DocumentDetail />} />
          <Route path="/api-docs" element={<ApiDocs />} />
        </Routes>
      </main>
      <Footer />
      <AuthModal />
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <LanguageProvider>
        <AuthProvider>
          <Layout />
        </AuthProvider>
      </LanguageProvider>
    </HashRouter>
  );
}