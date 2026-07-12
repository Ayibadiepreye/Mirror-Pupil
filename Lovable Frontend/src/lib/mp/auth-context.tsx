/**
 * Authentication Context
 * Manages Firebase auth state and user permissions
 */

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { onAuthStateChanged, type User } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { API_BASE_URL } from './api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isSuperAdmin: boolean;
  isApproved: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  isSuperAdmin: false,
  isApproved: false
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [isApproved, setIsApproved] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      
      if (firebaseUser) {
        // Fetch user info from backend
        try {
          const token = await firebaseUser.getIdToken();
          const response = await fetch(`${API_BASE_URL}/api/users/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          if (response.ok) {
            const userData = await response.json();
            setIsSuperAdmin(userData.is_super_admin || false);
            setIsApproved(userData.is_approved || false);
          } else if (response.status === 403) {
            // User not approved or doesn't exist
            setIsApproved(false);
            setIsSuperAdmin(false);
          } else {
            // Other errors
            console.error('Failed to fetch user data:', response.statusText);
            setIsApproved(false);
            setIsSuperAdmin(false);
          }
        } catch (error) {
          console.error('Failed to fetch user data:', error);
          setIsApproved(false);
          setIsSuperAdmin(false);
        }
      } else {
        setIsSuperAdmin(false);
        setIsApproved(false);
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, isSuperAdmin, isApproved }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
