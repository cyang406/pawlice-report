import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client.js'
import EvidenceImage from '../components/EvidenceImage.jsx'
import EventForm from '../components/EventForm.jsx'
import MugshotCropper from '../components/MugshotCropper.jsx'
import PetImage from '../components/PetImage.jsx'
import { eventTypeByValue } from '../eventTypes.js'

const dateFormat = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
})

export default function PetProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [pet, setPet] = useState(null)
  const [events, setEvents] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState(location.state?.uploadError || '')
  const [uploadingPet, setUploadingPet] = useState(false)
  const [pendingMugshot, setPendingMugshot] = useState(null)
  const [uploadingEventId, setUploadingEventId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [deletingPet, setDeletingPet] = useState(false)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    Promise.all([api.getPet(id), api.listEvents(id), api.getStats(id)])
      .then(([petData, eventData, statData]) => {
        if (active) {
          setPet(petData)
          setEvents(eventData)
          setStats(statData)
        }
      })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [id, retry])

  async function refreshActivity() {
    const [eventData, statData] = await Promise.all([api.listEvents(id), api.getStats(id)])
    setEvents(eventData)
    setStats(statData)
  }

  async function handleAddEvent(payload, imageFile) {
    setActionError('')
    const entry = await api.createEvent(id, payload)
    let uploadError = ''
    if (imageFile) {
      try {
        await api.uploadEventImage(entry.id, imageFile)
      } catch (err) {
        uploadError = `Entry saved, but the photo upload failed: ${err.message} You can retry from the journal entry.`
      }
    }
    try {
      await refreshActivity()
    } catch {
      setActionError('Entry saved, but the case file could not refresh. Reload the page to see it.' + (uploadError ? ` ${uploadError}` : ''))
      return
    }
    if (uploadError) setActionError(uploadError)
  }

  function handlePetImage(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setActionError('')
    setPendingMugshot(file)
  }

  async function saveMugshot(file) {
    setUploadingPet(true)
    try {
      setPet(await api.uploadPetImage(id, file))
      setPendingMugshot(null)
    } catch (err) {
      throw new Error(`Mugshot upload failed: ${err.message}`)
    } finally {
      setUploadingPet(false)
    }
  }

  async function handleEventImage(eventId, event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setActionError('')
    setUploadingEventId(eventId)
    try {
      const updated = await api.uploadEventImage(eventId, file)
      setEvents((current) => current.map((entry) => entry.id === eventId ? updated : entry))
    } catch (err) {
      setActionError(`Photo upload failed: ${err.message}`)
    } finally {
      setUploadingEventId(null)
    }
  }

  async function handleDelete(eventId) {
    if (!window.confirm('Remove this entry from the case file?')) return
    setActionError('')
    setDeletingId(eventId)
    try {
      await api.deleteEvent(eventId)
      try {
        await refreshActivity()
      } catch {
        setActionError('Entry deleted, but the case file could not refresh. Reload the page to update it.')
      }
    } catch (err) {
      setActionError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleDeletePet() {
    if (!window.confirm(`Delete ${pet.name}'s profile and all ${events.length} journal entries? This cannot be undone.`)) return
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
            <p className="profile-subtitle">Part criminal record, part life journal. Investigation ongoing.</p>
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
          <input type="file" accept="image/*,.heic,.heif,.tif,.tiff,.avif" onChange={handlePetImage} disabled={uploadingPet || Boolean(pendingMugshot) || deletingPet} aria-label="Upload or replace suspect mugshot" />
        </label>
        <button type="button" onClick={handleDeletePet} disabled={deletingPet}>
          {deletingPet ? 'Deleting profile...' : 'Delete suspect profile'}
        </button>
      </div>
      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <section className="stats-section" aria-labelledby="stats-title">
        <div className="section-heading"><span id="stats-title">CASE STATISTICS</span><span>{stats.total_events} JOURNAL ENTRIES</span></div>
        <div className="stats-grid">
          <div className="stat-card stat-card--incident"><span>INCIDENTS</span><strong>{stats.incident_count}</strong><small>ON RECORD</small></div>
          <div className="stat-card stat-card--good-conduct"><span>GOOD CONDUCT</span><strong>{stats.good_conduct_count}</strong><small>COMMENDATIONS</small></div>
          <div className="stat-card stat-card--funny-moment"><span>FUNNY MOMENTS</span><strong>{stats.funny_moment_count}</strong><small>UNUSUAL ACTIVITY</small></div>
          <div className="stat-card stat-card--wellness"><span>WELLNESS</span><strong>{stats.wellness_count}</strong><small>CHECKS ON FILE</small></div>
        </div>
        <div className="offense-heading">OFFENSE DETAILS / INCIDENTS ONLY</div>
        <div className="crime-stats-grid">
          <div className="stat-card stat-card-detail"><span>CRIMES THIS WEEK</span><strong>{stats.incidents_this_week}</strong><small>MON–SUN · UTC</small></div>
          <div className="stat-card stat-card-detail"><span>TOP OFFENSE</span><strong className="stat-category">{stats.most_common_category || '—'}</strong><small>MOST COMMON CRIME</small></div>
          <div className="stat-card stat-card-detail"><span>AVG. MENACE LEVEL</span><strong>{stats.average_severity == null ? '—' : stats.average_severity}</strong><small>{stats.average_severity == null ? 'NO DATA' : 'OUT OF 5'}</small></div>
        </div>
      </section>

      <div className="case-work-grid">
        <section className="event-section" aria-labelledby="events-title">
          <div className="section-heading"><span id="events-title">CASE FILE / PET JOURNAL</span><span>{events.length} ENTRIES</span></div>
          {events.length === 0 ? (
            <div className="event-empty">
              <span aria-hidden="true">✓</span>
              <h2>No suspicious activity on record... yet.</h2>
              <p>Crimes, good deeds, odd moments, and wellness checks all belong in this case file. Add the first entry when something happens.</p>
            </div>
          ) : (
            <div className="event-list">
              {events.map((entry) => {
                const type = eventTypeByValue[entry.event_type]
                return <article className={`event-card event-card--${entry.event_type.toLowerCase().replace('_', '-')}`} key={entry.id}>
                  <div className="event-card-top">
                    <span>{type.tag} / #{String(entry.id).padStart(4, '0')}</span>
                    <span>{dateTimeFormat.format(new Date(entry.event_time))}</span>
                  </div>
                  <div className="event-card-body">
                    <div className="event-title-row">
                      <h3>{entry.category}</h3>
                      {entry.event_type === 'INCIDENT' && <span className="severity-badge">SEVERITY {entry.severity}/5</span>}
                    </div>
                    <p>{entry.description}</p>
                    <EvidenceImage src={entry.image_url} label={`${entry.category} photo`} />
                    <div className="event-card-footer">
                      <span>{entry.image_url ? entry.event_type === 'INCIDENT' ? 'EVIDENCE ATTACHED' : 'PHOTO ON FILE' : 'NO PHOTO ON FILE'}</span>
                      <label className="inline-upload">
                        <span>{uploadingEventId === entry.id ? 'Uploading...' : entry.image_url ? 'Replace photo' : 'Upload photo'}</span>
                        <input type="file" accept="image/*,.heic,.heif,.tif,.tiff,.avif" onChange={(event) => handleEventImage(entry.id, event)} disabled={uploadingEventId !== null || deletingId !== null || deletingPet} aria-label={`Upload or replace photo for entry ${entry.id}`} />
                      </label>
                      <button type="button" onClick={() => handleDelete(entry.id)} disabled={deletingId !== null}>
                        {deletingId === entry.id ? 'Deleting...' : 'Delete entry'}
                      </button>
                    </div>
                  </div>
                </article>
              })}
            </div>
          )}
        </section>

        <aside className="report-column"><EventForm onAddEvent={handleAddEvent} /></aside>
      </div>
      {pendingMugshot && <MugshotCropper file={pendingMugshot} onSave={saveMugshot} onCancel={() => setPendingMugshot(null)} />}
    </div>
  )
}
