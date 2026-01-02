import React, { useState } from 'react';
import { X, LogIn } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLanguage } from '../store/language';
import { useAuth } from '../store/auth';

export function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, login } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const { t } = useLanguage();

  if (!isAuthModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSent(true);
    // Simulate magic link delay then auto-login for demo purposes
    // In a real app, user would click the link in email
    setTimeout(() => {
      login(email);
      setSent(false);
      setEmail('');
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.98 }}
        className="bg-card w-full max-w-md border border-border rounded-lg shadow-lg p-6 relative"
      >
        <button 
          onClick={closeAuthModal}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={20} />
        </button>

        <div className="text-center mb-6">
          <div className="bg-primary/10 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-primary">
            <LogIn size={24} />
          </div>
          <h2 className="text-xl font-bold text-foreground">
            {t('auth.modal_title')}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
             {sent ? t('auth.check_email') : t('nav.continue_email')}
          </p>
        </div>

        {!sent ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
                {t('auth.email_label')}
              </label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full bg-background border border-input rounded-md px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-input transition-all"
              />
            </div>
            <button 
              type="submit"
              className="w-full bg-primary text-primary-foreground py-2.5 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
            >
              {t('auth.submit')}
            </button>
          </form>
        ) : (
          <div className="text-center py-4">
            <div className="animate-pulse text-primary font-medium">
              {t('auth.sent')}
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}