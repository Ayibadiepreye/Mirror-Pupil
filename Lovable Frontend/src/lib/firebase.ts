/**
 * Firebase Authentication Configuration
 * Handles Google OAuth and Email/Password authentication
 */

import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInWithPopup, 
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  type User
} from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Google OAuth Provider
export const googleProvider = new GoogleAuthProvider();

// Auth helper functions
export const loginWithGoogle = () => signInWithPopup(auth, googleProvider);

export const loginWithEmail = (email: string, password: string) => 
  signInWithEmailAndPassword(auth, email, password);

export const registerWithEmail = (email: string, password: string) => 
  createUserWithEmailAndPassword(auth, email, password);

export const logout = () => signOut(auth);

// Type export
export type { User };
