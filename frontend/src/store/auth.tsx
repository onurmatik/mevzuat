import React, { createContext, useContext, useState, ReactNode } from 'react';

interface User {
  email: string;
  name?: string;
  isPro?: boolean;
  apiKey?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string) => void;
  logout: () => void;
  upgradeToPro: () => void;
  isAuthModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const login = (email: string) => {
    // Simulate finding existing user or creating new one
    // For demo, if email contains "pro", make them pro automatically
    const isPro = email.includes('pro');
    const apiKey = isPro ? 'mvz_live_' + Math.random().toString(36).substring(2, 15) : undefined;
    
    setUser({ 
      email, 
      isPro,
      apiKey
    });
    setIsAuthModalOpen(false);
  };

  const logout = () => {
    setUser(null);
  };

  const upgradeToPro = () => {
    if (!user) {
      openAuthModal();
      return;
    }
    
    // Simulate API call to upgrade
    const newApiKey = 'mvz_live_' + Math.random().toString(36).substring(2, 15);
    setUser({ ...user, isPro: true, apiKey: newApiKey });
  };

  const openAuthModal = () => setIsAuthModalOpen(true);
  const closeAuthModal = () => setIsAuthModalOpen(false);

  return (
    <AuthContext.Provider 
      value={{ 
        isAuthenticated: !!user, 
        user, 
        login, 
        logout, 
        upgradeToPro,
        isAuthModalOpen, 
        openAuthModal, 
        closeAuthModal 
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}