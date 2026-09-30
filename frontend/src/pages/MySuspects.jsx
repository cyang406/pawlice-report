import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import PetImage from '../components/PetImage.jsx'

export default function MySuspects() {
  const [pets, setPets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true
    api.listPets()
      .then((data) => { if (active) setPets(data) })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [retry])

  return (
    <div className="page-container">
      <section className="page-hero roster-hero">
        <div>
          <p className="eyebrow"><span className="status-dot" /> PAWLICE DEPARTMENT / ACTIVE FILES</p>
          <h1>My <em>Suspects</em></h1>
          <p className="hero-copy">The faces behind the missing snacks, mysterious noises, and suspiciously overturned plants.</p>
        </div>
        <Link className="button button-primary hero-button" to="/pets/new"><span>+</span> Add Suspect</Link>
      </section>

      <div className="section-heading">
        <span>THE ROSTER</span>
        <span>{loading ? 'LOCATING FILES...' : `${pets.length} ${pets.length === 1 ? 'SUSPECT' : 'SUSPECTS'} ON FILE`}</span>
      </div>

      {loading ? (
        <div className="state-panel" role="status"><span className="loading-mark" /> Retrieving suspect files...</div>
      ) : error ? (
        <div className="state-panel" role="alert">
          <h2>Couldn’t open the records room.</h2>
          <p>{error}</p>
          <button className="button button-outline" onClick={() => { setError(''); setLoading(true); setRetry((n) => n + 1) }}>Try again</button>
        </div>
      ) : pets.length === 0 ? (
        <div className="empty-roster">
          <span className="empty-stamp" aria-hidden="true">?</span>
          <p className="eyebrow">NO SUSPECTS ON FILE</p>
          <h2>A suspiciously clean record.</h2>
          <p>Every great investigation starts somewhere. Add your first furry person of interest.</p>
          <Link className="button button-primary" to="/pets/new">+ Add your first suspect</Link>
        </div>
      ) : (
        <div className="pet-grid">
          {pets.map((pet) => (
            <article className="pet-card" key={pet.id}>
              <div className="pet-card-photo">
                <PetImage src={pet.image_url} name={pet.name} />
                <span className="card-id">SUSPECT NO. {String(pet.id).padStart(4, '0')}</span>
              </div>
              <div className="pet-card-body">
                <p className="eyebrow">PERSON OF INTEREST</p>
                <h2>{pet.name}</h2>
                <div className="pet-card-details">
                  <span><small>SPECIES</small>{pet.species}</span>
                  <span><small>BREED</small>{pet.breed || 'Unknown'}</span>
                </div>
                <Link className="card-link" to={`/pets/${pet.id}`}>
                  View criminal profile <span aria-hidden="true">↗</span>
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
