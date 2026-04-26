import { useAuth } from './AuthContext'
import { firebaseReady } from './firebase'
import './Header.css'

export default function Header() {
  const { user, loginWithGoogle, logout } = useAuth()

  // Still resolving auth state
  if (user === undefined) {
    return <header className="app-header" />
  }

  return (
    <header className="app-header">
      <div className="header-right">
        {user ? (
          <div className="user-info">
            {user.photoURL && (
              <img
                src={user.photoURL}
                alt={user.displayName ?? 'User avatar'}
                className="user-avatar"
                referrerPolicy="no-referrer"
              />
            )}
            <span className="user-name">{user.displayName ?? user.email}</span>
            <button className="btn-logout" onClick={logout}>
              Sign out
            </button>
          </div>
        ) : (
          <button
            className="btn-login"
            onClick={loginWithGoogle}
            disabled={!firebaseReady}
            title={!firebaseReady ? 'Auth not configured' : undefined}
          >
            Sign in with Google
          </button>
        )}
      </div>
    </header>
  )
}
