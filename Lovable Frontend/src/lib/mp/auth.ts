// Mirror Pupil — Firebase Authentication Integration
//
// This module integrates Firebase Authentication with the Mirror Pupil backend.
// It handles Google Sign-In and Email/Password authentication, retrieves JWT tokens,
// and stores session data in localStorage.

import { 
  signInWithPopup, 
  signInWithEmailAndPassword,
  GoogleAuthProvider,
  getAuth 
} from 'firebase/auth';
import { app } from '../firebase';

const SESSION_KEY = "mp.session.v1";
const auth = getAuth(app);

export interface MpSession {
  token: string;       // Firebase JWT token
  email: string;
  displayName: string;
  provider: "google" | "password";
}

export function getSession(): MpSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as MpSession) : null;
  } catch {
    return null;
  }
}

export function setSession(s: MpSession) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(s));
  window.dispatchEvent(new Event("mp:session"));
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event("mp:session"));
}

/**
 * Sign in with email and password using Firebase Authentication
 */
export async function signInWithPassword(email: string, password: string): Promise<MpSession> {
  if (!email || !password) throw new Error("Email and password required");
  
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    const token = await user.getIdToken();
    
    const session: MpSession = {
      token,
      email: user.email || email,
      displayName: user.displayName || email.split("@")[0],
      provider: "password",
    };
    
    setSession(session);
    return session;
  } catch (error: any) {
    console.error("Firebase email/password sign-in failed:", error);
    throw new Error(error.message || "Failed to sign in with email and password");
  }
}

/**
 * Sign in with Google using Firebase Authentication popup
 */
export async function signInWithGoogle(): Promise<MpSession> {
  const provider = new GoogleAuthProvider();
  
  try {
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    const token = await user.getIdToken();
    
    const session: MpSession = {
      token,
      email: user.email || "",
      displayName: user.displayName || user.email?.split("@")[0] || "User",
      provider: "google",
    };
    
    setSession(session);
    return session;
  } catch (error: any) {
    console.error("Firebase Google sign-in failed:", error);
    throw new Error(error.message || "Failed to sign in with Google");
  }
}

/**
 * Sign out and clear session
 */
export async function signOut() {
  try {
    await auth.signOut();
    clearSession();
  } catch (error) {
    console.error("Firebase sign-out failed:", error);
    clearSession(); // Clear session anyway
  }
}

/**
 * Get current Firebase user's JWT token
 * Useful for refreshing the token
 */
export async function refreshToken(): Promise<string | null> {
  const currentUser = auth.currentUser;
  if (!currentUser) return null;
  
  try {
    const token = await currentUser.getIdToken(true); // Force refresh
    const session = getSession();
    if (session) {
      session.token = token;
      setSession(session);
    }
    return token;
  } catch (error) {
    console.error("Failed to refresh token:", error);
    return null;
  }
}
