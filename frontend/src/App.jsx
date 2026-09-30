import { Link, Route, Routes } from 'react-router-dom'
import MySuspects from './pages/MySuspects.jsx'
import AddPet from './pages/AddPet.jsx'
import PetProfile from './pages/PetProfile.jsx'

export default function App() {
  return <div className="app-shell">
    <header className="site-header">
      <Link className="brand" to="/" aria-label="Pawlice Report home">
        <span className="brand-mark" aria-hidden="true">✦</span>
        <span><strong>PAWLICE<span className="brand-accent">.</span> REPORT</strong>
          <small>DEPARTMENT OF DOMESTIC MISCHIEF</small></span>
      </Link>
      <nav aria-label="Main navigation"><Link to="/">MY SUSPECTS</Link><Link className="nav-add" to="/pets/new">+ ADD SUSPECT</Link></nav>
    </header>
    <main><Routes>
      <Route path="/" element={<MySuspects />} />
      <Route path="/pets/new" element={<AddPet />} />
      <Route path="/pets/:id" element={<PetProfile />} />
      <Route path="*" element={<div className="page-container missing-page"><h1>File not found.</h1><Link to="/">Back to suspects</Link></div>} />
    </Routes></main>
    <footer className="site-footer"><span>PAWLICE DEPARTMENT · DOMESTIC MISCHIEF</span><span>ALL SUSPECTS ARE PRESUMED ADORABLE</span></footer>
  </div>
}
