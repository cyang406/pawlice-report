import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api } from './api/client.js'
import MySuspects from './pages/MySuspects.jsx'
import AddPet from './pages/AddPet.jsx'
import PetProfile from './pages/PetProfile.jsx'
import PawliceReport from './pages/PawliceReport.jsx'
import AuthPage from './pages/AuthPage.jsx'

function PrivatePage({ user, children }) {
  const location = useLocation()
  return user ? children : <Navigate to="/login" state={{ from: location }} replace />
}

export default function App() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [headerError, setHeaderError] = useState('')

  useEffect(() => {
    let active = true
    api.me()
      .then((account) => { if (active) setUser(account) })
      .catch(() => { if (active) setUser(null) })
      .finally(() => { if (active) setCheckingSession(false) })
    return () => { active = false }
  }, [])

  async function handleLogout() {
    setHeaderError('')
    try {
      await api.logout()
      setUser(null)
      navigate('/login')
    } catch (err) {
      setHeaderError(err.message)
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Pawlice Report home">
          <span className="brand-mark" aria-hidden="true">✦</span>
          <span>
            <strong>PAWLICE<span className="brand-accent">.</span> REPORT</strong>
            <small>DEPARTMENT OF DOMESTIC MISCHIEF</small>
          </span>
        </Link>
        <nav className={user ? 'nav-authenticated' : 'nav-guest'} aria-label="Main navigation">
          {user ? <>
            <Link to="/">MY SUSPECTS</Link>
            <Link className="nav-add" to="/pets/new">+ ADD SUSPECT</Link>
            <span className="nav-account" title={user.email}>{user.email}</span>
            <button className="nav-logout" type="button" onClick={handleLogout}>SIGN OUT</button>
          </> : <>
            <Link to="/login">SIGN IN</Link>
            <Link className="nav-add" to="/register">CREATE ACCOUNT</Link>
          </>}
        </nav>
      </header>

      {headerError && <p className="header-error" role="alert">{headerError}</p>}

      <main>
        {checkingSession ? <div className="page-container profile-loading" role="status"><span className="loading-mark" /> Checking desk access...</div> : <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage mode="login" onAuthenticated={setUser} />} />
          <Route path="/register" element={user ? <Navigate to="/" replace /> : <AuthPage mode="register" onAuthenticated={setUser} />} />
          <Route path="/" element={<PrivatePage user={user}><MySuspects /></PrivatePage>} />
          <Route path="/pets/new" element={<PrivatePage user={user}><AddPet /></PrivatePage>} />
          <Route path="/pets/:id" element={<PrivatePage user={user}><PetProfile /></PrivatePage>} />
          <Route path="/pets/:id/report" element={<PrivatePage user={user}><PawliceReport /></PrivatePage>} />
          <Route path="*" element={
            <div className="page-container missing-page">
              <p className="eyebrow">FILE NOT FOUND</p>
              <h1>Nothing to investigate here.</h1>
              <Link className="button button-primary" to="/">Back to suspects</Link>
            </div>
          } />
        </Routes>}
      </main>

      <footer className="site-footer">
        <span>PAWLICE DEPARTMENT · EST. WHENEVER THE TREATS WENT MISSING</span>
        <span>ALL SUSPECTS ARE PRESUMED ADORABLE</span>
      </footer>
    </div>
  )
}
