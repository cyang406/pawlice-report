import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client.js'
import EvidenceImage from '../components/EvidenceImage.jsx'
import IncidentForm from '../components/IncidentForm.jsx'
import PetImage from '../components/PetImage.jsx'

const dateFormat = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
})

export default function PetProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [pet, setPet] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState(location.state?.uploadError || '')
  const [uploadingPet, setUploadingPet] = useState(false)
  const [uploadingIncidentId, setUploadingIncidentId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [deletingPet, setDeletingPet] = useState(false)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    Promise.all([api.getPet(id), api.listIncidents(id), api.getStats(id)])
      .then(([petData, incidentData, statData]) => {
        if (active) {
          setPet(petData)
          setIncidents(incidentData)
          setStats(statData)
        }
      })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id, retry])

  async function refreshActivity() {
    const [incidentData, statData] = await Promise.all([api.listIncidents(id), api.getStats(id)])
    setIncidents(incidentData)
    setStats(statData)
  }

  async function handleReport(payload, imageFile) {
    setActionError('')
    const incident = await api.createIncident(id, payload)
    let uploadError = ''
    if (imageFile) {
      try {
        await api.uploadIncidentImage(incident.id, imageFile)
      } catch (err) {
        uploadError = `Incident saved, but the evidence upload failed: ${err.message} You can retry from the incident card.`
      }
    }
    try {
      await refreshActivity()
    } catch {
      setActionError('Incident saved, but the case file could not refresh. Reload the page to see it.' + (uploadError ? ` ${uploadError}` : ''))
      return
    }
    if (uploadError) setActionError(uploadError)
  }

  async function handlePetImage(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setActionError('')
    setUploadingPet(true)
    try {
      setPet(await api.uploadPetImage(id, file))
    } catch (err) {
      setActionError(`Mugshot upload failed: ${err.message}`)
    } finally {
      setUploadingPet(false)
    }
  }

  async function handleIncidentImage(incidentId, event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setActionError('')
    setUploadingIncidentId(incidentId)
    try {
      const updated = await api.uploadIncidentImage(incidentId, file)
      setIncidents((current) => current.map((incident) => incident.id === incidentId ? updated : incident))
    } catch (err) {
      setActionError(`Evidence upload failed: ${err.message}`)
    } finally {
      setUploadingIncidentId(null)
    }
  }

  async function handleDelete(incidentId) {
    if (!window.confirm('Remove this incident from the case file?')) return
    setActionError('')
    setDeletingId(incidentId)
    try {
      await api.deleteIncident(incidentId)
      try {
        await refreshActivity()
      } catch {
        setActionError('Incident deleted, but the case file could not refresh. Reload the page to update it.')
      }
    } catch (err) {
      setActionError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleDeletePet() {
    if (!window.confirm(`Delete ${pet.name}'s profile and all ${incidents.length} incident reports? This cannot be undone.`)) return
    setActionError('')
    setDeletingPet(true)
    try {
      await api.deletePet(id)
      navigate('/')
    } catch (err) {
      setActionError(err.message)
      setDeletingPet(false)
    }
  }

  if (loading) {
    return <div className="page-container profile-loading" role="status"><span className="loading-mark" /> Retrieving case file...</div>
  }

  if (error || !pet || !stats) {
    return (
      <div className="page-container missing-page" role="alert">
        <p className="eyebrow">CASE FILE UNAVAILABLE</p>
        <h1>{error === 'Pet not found' ? 'Suspect not found.' : 'The records room is closed.'}</h1>
        <p>{error}</p>
        <div className="missing-actions">
          <Link className="button button-outline" to="/">Back to suspects</Link>
          {error !== 'Pet not found' && <button className="button button-primary" onClick={() => { setError(''); setLoading(true); setRetry((n) => n + 1) }}>Try again</button>}
        </div>
      </div>
    )
  }

  return (
    <div className="page-container profile-page">
      <Link className="back-link" to="/">← Back to suspect roster</Link>

      <section className="profile-file">
        <div className="file-strip"><span>PAWLICE DEPARTMENT / CASE FILE</span><span>NO. {String(pet.id).padStart(4, '0')}</span></div>
        <div className="profile-main">
          <div className="profile-photo">
            <PetImage src={pet.image_url} name={pet.name} />
            <span>MUGSHOT / EXHIBIT A</span>
          </div>
          <div className="profile-info">
            <p className="eyebrow">CRIMINAL PROFILE · PERSON OF INTEREST</p>
            <h1>{pet.name}</h1>
            <p className="profile-subtitle">Known for looking innocent. Investigation ongoing.</p>
            <div className="profile-facts">
              <div><small>SPECIES</small><strong>{pet.species}</strong></div>
              <div><small>BREED</small><strong>{pet.breed || 'Unknown'}</strong></div>
              {pet.birthday && <div><small>DATE OF BIRTH</small><strong>{dateFormat.format(new Date(`${pet.birthday}T12:00:00`))}</strong></div>}
              <div><small>FILE OPENED</small><strong>{dateFormat.format(new Date(pet.created_at))}</strong></div>
            </div>
          </div>
          <div className={`profile-stamp ${stats.total_incidents >= 2 ? '' : 'stamp-muted'}`} aria-label={stats.total_incidents >= 2 ? 'Repeat offender' : 'Under investigation'}>
            {stats.total_incidents >= 2 ? <>REPEAT<br />OFFENDER</> : <>UNDER<br />INVESTIGATION</>}
          </div>
        </div>
      </section>

      <div className="profile-actions">
        <span>CASE FILE NO. {String(pet.id).padStart(4, '0')}</span>
        <label className="inline-upload">
          <span>{uploadingPet ? 'Uploading mugshot...' : pet.image_url ? 'Replace mugshot' : 'Upload mugshot'}</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePetImage} disabled={uploadingPet || deletingPet} aria-label="Upload or replace suspect mugshot" />
        </label>
        <button type="button" onClick={handleDeletePet} disabled={deletingPet}>
          {deletingPet ? 'Deleting profile...' : 'Delete suspect profile'}
        </button>
      </div>
      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <section className="stats-section" aria-labelledby="stats-title">
        <div className="section-heading"><span id="stats-title">CASE STATISTICS</span><span>AT A GLANCE</span></div>
        <div className="stats-grid">
          <div className="stat-card"><span>TOTAL INCIDENTS</span><strong>{stats.total_incidents}</strong><small>ON RECORD</small></div>
          <div className="stat-card"><span>THIS WEEK</span><strong>{stats.incidents_this_week}</strong><small>MON–SUN · UTC</small></div>
          <div className="stat-card"><span>TOP OFFENSE</span><strong className="stat-category">{stats.most_common_category || '—'}</strong><small>MOST COMMON CATEGORY</small></div>
          <div className="stat-card"><span>AVG. SEVERITY</span><strong>{stats.average_severity == null ? '—' : stats.average_severity}</strong><small>{stats.average_severity == null ? 'NO DATA' : 'OUT OF 5'}</small></div>
        </div>
      </section>

      <div className="case-work-grid">
        <section className="incident-section" aria-labelledby="incidents-title">
          <div className="section-heading"><span id="incidents-title">INCIDENT LOG</span><span>{incidents.length} ENTRIES</span></div>
          {incidents.length === 0 ? (
            <div className="incident-empty">
              <span aria-hidden="true">✓</span>
              <h2>No crimes on record. Yet.</h2>
              <p>Either a model citizen or an exceptionally sneaky suspect. File the first report when evidence appears.</p>
            </div>
          ) : (
            <div className="incident-list">
              {incidents.map((incident) => (
                <article className="incident-card" key={incident.id}>
                  <div className="incident-card-top">
                    <span>INCIDENT #{String(incident.id).padStart(4, '0')}</span>
                    <span>{dateTimeFormat.format(new Date(incident.incident_time))}</span>
                  </div>
                  <div className="incident-card-body">
                    <div className="incident-title-row">
                      <h3>{incident.category}</h3>
                      <span className="severity-badge">SEVERITY {incident.severity}/5</span>
                    </div>
                    <p>{incident.description}</p>
                    <EvidenceImage src={incident.image_url} />
                    <div className="incident-card-footer">
                      <span>{incident.image_url ? 'EVIDENCE ATTACHED' : 'NO PHOTO EVIDENCE'}</span>
                      <label className="inline-upload">
                        <span>{uploadingIncidentId === incident.id ? 'Uploading...' : incident.image_url ? 'Replace evidence' : 'Upload evidence'}</span>
                        <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => handleIncidentImage(incident.id, event)} disabled={uploadingIncidentId !== null || deletingId !== null || deletingPet} aria-label={`Upload or replace evidence for incident ${incident.id}`} />
                      </label>
                      <button type="button" onClick={() => handleDelete(incident.id)} disabled={deletingId !== null}>
                        {deletingId === incident.id ? 'Deleting...' : 'Delete report'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <aside className="report-column"><IncidentForm onReport={handleReport} /></aside>
      </div>
    </div>
  )
}
