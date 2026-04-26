import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const apiKey = import.meta.env.VITE_FIREBASE_API_KEY

export const firebaseReady = Boolean(apiKey)

export let auth = null
export let googleProvider = null

if (firebaseReady) {
  const app = initializeApp({
    apiKey,
    authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId:             import.meta.env.VITE_FIREBASE_APP_ID,
  })
  auth = getAuth(app)
  googleProvider = new GoogleAuthProvider()
}
