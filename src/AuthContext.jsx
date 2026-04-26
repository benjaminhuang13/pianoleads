import { createContext, useContext, useEffect, useState } from "react";
import { onAuthStateChanged, signInWithPopup, signOut } from "firebase/auth";
import { doc, getDoc } from "firebase/firestore";
import { auth, googleProvider, db, firebaseReady } from "./firebase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(firebaseReady ? undefined : null);
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    if (!firebaseReady) return;
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser ?? null);
    });
    return unsubscribe;
  }, []);

  async function loginWithGoogle() {
    setAuthError(null);
    const result = await signInWithPopup(auth, googleProvider);
    const email = result.user.email;

    const snap = await getDoc(doc(db, "whitelist_users", email));
    if (!snap.exists()) {
      await signOut(auth);
      setAuthError(`User not authorized.`);
      return;
    }
  }

  async function logout() {
    setAuthError(null);
    await signOut(auth);
  }

  return (
    <AuthContext.Provider value={{ user, authError, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
