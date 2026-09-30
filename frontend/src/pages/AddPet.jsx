import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import PetImage from '../components/PetImage.jsx'

const initialForm = { name: '', species: '', breed: '', birthday: '', image_url: '' }

export default function AddPet() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [imageFile, setImageFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!imageFile) {
      setPreviewUrl('')
      return
    }
    const url = URL.createObjectURL(imageFile)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageFile])

  function update(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const pet = await api.createPet({
        name: form.name.trim(),
        species: form.species.trim(),
        breed: form.breed.trim() || null,
        birthday: form.birthday || null,
        image_url: imageFile ? null : form.image_url.trim() || null,
      })
      if (imageFile) {
        try {
          await api.uploadPetImage(pet.id, imageFile)
        } catch (err) {
          navigate(`/pets/${pet.id}`, {
            state: { uploadError: `Case file created, but the mugshot upload failed: ${err.message}` },
          })
          return
        }
      }
      navigate(`/pets/${pet.id}`)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="page-container form-page">
      <Link className="back-link" to="/">← Back to suspect roster</Link>
      <div className="form-heading">
        <p className="eyebrow">NEW CASE FILE / INTAKE FORM 01</p>
        <h1>Add a <em>Suspect</em></h1>
        <p>Every repeat offender has to start somewhere. Let’s get the basics on record.</p>
      </div>

      <div className="intake-layout">
        <form className="paper-panel intake-form" onSubmit={handleSubmit}>
          <div className="panel-topline"><span>PAWLICE DEPARTMENT</span><span>CONFIDENTIAL-ish</span></div>
          <h2>Suspect particulars</h2>
          <p className="field-note">Fields marked * are required.</p>

          <div className="field-grid">
            <label className="field">
              <span>NAME *</span>
              <input name="name" value={form.name} onChange={update} maxLength={100} required placeholder="e.g. Mochi" />
            </label>
            <label className="field">
              <span>SPECIES *</span>
              <input name="species" value={form.species} onChange={update} maxLength={100} required placeholder="e.g. Cat" />
            </label>
            <label className="field">
              <span>BREED</span>
              <input name="breed" value={form.breed} onChange={update} maxLength={100} placeholder="e.g. Domestic shorthair" />
            </label>
            <label className="field">
              <span>BIRTHDAY</span>
              <input type="date" name="birthday" value={form.birthday} onChange={update} />
            </label>
            <label className="field field-full">
              <span>UPLOAD MUGSHOT</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setImageFile(event.target.files?.[0] || null)} />
              <small>Choose a photo from Photos or your files · 5 MB maximum. Some formats preview after upload. A selected file takes priority over a pasted URL.</small>
            </label>
            <label className="field field-full">
              <span>MUGSHOT IMAGE URL</span>
              <input name="image_url" value={form.image_url} onChange={update} maxLength={2048} placeholder="https://example.com/mochi.jpg" />
              <small>Or paste a link to an existing image.</small>
            </label>
          </div>

          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="form-actions">
            <Link className="button button-quiet" to="/">Cancel</Link>
            <button className="button button-primary" type="submit" disabled={submitting}>
              {submitting ? 'Opening file...' : 'Create case file →'}
            </button>
          </div>
        </form>

        <aside className="intake-preview">
          <div className="preview-label"><span>PREVIEW</span><span>FILE NO. PENDING</span></div>
          <PetImage src={previewUrl || form.image_url.trim()} name={form.name.trim() || 'this suspect'} />
          <div className="preview-caption">
            <span className="eyebrow">POTENTIAL PERSON OF INTEREST</span>
            <strong>{form.name.trim() || 'Unknown suspect'}</strong>
            <span>{form.species.trim() || 'Species unknown'}</span>
          </div>
          <span className="preview-stamp">UNDER<br />INVESTIGATION</span>
        </aside>
      </div>
    </div>
  )
}
