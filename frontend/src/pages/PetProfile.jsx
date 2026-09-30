import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client.js'
import EvidenceImage from '../components/EvidenceImage.jsx'
import IncidentForm from '../components/IncidentForm.jsx'
import PetImage from '../components/PetImage.jsx'

export default function PetProfile() {
  const { id } = useParams()
  const [pet, setPet] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  useEffect(() => {
    let active = true
    Promise.all([api.getPet(id), api.listIncidents(id), api.getStats(id)])
      .then(([petData, incidentData, statData]) => { if (active) { setPet(petData); setIncidents(incidentData); setStats(statData) } })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id])
  async function refresh() {
    const [incidentData, statData] = await Promise.all([api.listIncidents(id), api.getStats(id)])
    setIncidents(incidentData); setStats(statData)
  }
  async function report(payload) { await api.createIncident(id, payload); await refresh() }
  async function remove(incidentId) {
    if (!window.confirm('Remove this incident from the case file?')) return
    setActionError(''); setDeletingId(incidentId)
    try { await api.deleteIncident(incidentId); await refresh() }
    catch (err) { setActionError(err.message) }
    finally { setDeletingId(null) }
  }
  if (loading) return <div className="page-container profile-loading" role="status">Retrieving case file...</div>
  if (error || !pet || !stats) return <div className="page-container missing-page" role="alert"><h1>Case file unavailable</h1><p>{error}</p><Link to="/">Back to suspects</Link></div>
  return <div className="page-container profile-page">
    <Link className="back-link" to="/">← Back to suspect roster</Link>
    <section className="profile-file"><div className="file-strip"><span>PAWLICE DEPARTMENT / CASE FILE</span><span>NO. {String(pet.id).padStart(4, '0')}</span></div>
      <div className="profile-main"><div className="profile-photo"><PetImage src={pet.image_url} name={pet.name} /><span>MUGSHOT / EXHIBIT A</span></div>
        <div className="profile-info"><p className="eyebrow">CRIMINAL PROFILE · PERSON OF INTEREST</p><h1>{pet.name}</h1>
          <div className="profile-facts"><div><small>SPECIES</small><strong>{pet.species}</strong></div>
            <div><small>BREED</small><strong>{pet.breed || 'Unknown'}</strong></div>
            {pet.birthday && <div><small>DATE OF BIRTH</small><strong>{pet.birthday}</strong></div>}</div></div>
      </div></section>
    {actionError && <p className="form-error" role="alert">{actionError}</p>}
    <section className="stats-section"><div className="section-heading"><span>CASE STATISTICS</span><span>AT A GLANCE</span></div>
      <div className="stats-grid">
        <div className="stat-card"><span>TOTAL INCIDENTS</span><strong>{stats.total_incidents}</strong></div>
        <div className="stat-card"><span>THIS WEEK</span><strong>{stats.incidents_this_week}</strong></div>
        <div className="stat-card"><span>TOP OFFENSE</span><strong className="stat-category">{stats.most_common_category || '—'}</strong></div>
        <div className="stat-card"><span>AVG. SEVERITY</span><strong>{stats.average_severity ?? '—'}</strong></div>
      </div></section>
    <div className="case-work-grid"><section className="incident-section"><div className="section-heading"><span>INCIDENT LOG</span><span>{incidents.length} ENTRIES</span></div>
      {incidents.length === 0 ? <div className="incident-empty"><h2>No crimes on record. Yet.</h2></div> :
        <div className="incident-list">{incidents.map((incident) => <article className="incident-card" key={incident.id}>
          <div className="incident-card-top"><span>INCIDENT #{incident.id}</span><span>{new Date(incident.incident_time).toLocaleString()}</span></div>
          <div className="incident-card-body"><h3>{incident.category}</h3><p>{incident.description}</p><EvidenceImage src={incident.image_url} />
            <div className="incident-card-footer"><span>SEVERITY {incident.severity}/5</span>
              <button type="button" onClick={() => remove(incident.id)} disabled={deletingId !== null}>{deletingId === incident.id ? 'Deleting...' : 'Delete report'}</button></div>
          </div></article>)}</div>}</section>
      <aside className="report-column"><IncidentForm onReport={report} /></aside></div>
  </div>
}
