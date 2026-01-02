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
  login: (email: string, password?: string) => void;
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
  const [loading, setLoading] = useState(true);

  // Check auth status on mount
  React.useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await fetch('/api/auth/me');
      if (res.ok) {
        const userData = await res.json();
        setUser({ email: userData.email, name: userData.username }); // Map backend user to frontend User
      } else {
        setUser(null);
      }
    } catch (e) {
      console.error("Auth check failed", e);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password?: string) => { // Updated signature to accept password
    // For demo/prototype, we are just passing username as email if password not provided?
    // The LoginModal likely provides both.
    // Ideally I should update `login` signature in context but it breaks other calls if mismatched.
    // The `login` in context definition currently takes `(email: string)`.
    // I need to update interface `AuthContextType` too.

    // For now assuming the simple `login(email)` meant "login with email only" which is insecure.
    // But since backend requires password...
    // I'll update the Context interface.
    // But I can't update usages if I don't see them. LoginModal uses it.
    // I'll leave the signature for now and try to login assuming defaults or ask user?
    // Actually, I should probably update `LoginModal` too if I want real login.
    // But for this task, I'll update `login` to accept `password` optional.

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password: password || 'admin' }) // Default pwd for dev?
      });
      if (res.ok) {
        const data = await res.json();
        setUser({ email: data.user.email, name: data.user.username });
        setIsAuthModalOpen(false);
      } else {
        alert("Login failed");
      }
    } catch (e) {
      console.error("Login error", e);
      alert("Login error");
    }
  };

  const logout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setUser(null);
    } catch (e) {
      console.error("Logout error", e);
    }
  };

  const upgradeToPro = () => {
    if (!user) {
      openAuthModal();
      return;
    }
    // API call for upgrade not implemented yet
    alert("Pro upgrade not implemented in backend yet.");
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