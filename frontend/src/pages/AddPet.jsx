import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import PetImage from '../components/PetImage.jsx'

export default function AddPet() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', species: '', breed: '', birthday: '', image_url: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  function update(event) { setForm((current) => ({ ...current, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const pet = await api.createPet({ name: form.name.trim(), species: form.species.trim(),
        breed: form.breed.trim() || null, birthday: form.birthday || null, image_url: form.image_url.trim() || null })
      navigate(`/pets/${pet.id}`)
    } catch (err) { setError(err.message); setSubmitting(false) }
  }
  return <div className="page-container form-page">
    <Link className="back-link" to="/">← Back to suspect roster</Link>
    <div className="form-heading"><p className="eyebrow">NEW CASE FILE / INTAKE FORM 01</p><h1>Add a <em>Suspect</em></h1>
      <p>Every repeat offender has to start somewhere. Let’s get the basics on record.</p></div>
    <div className="intake-layout"><form className="paper-panel intake-form" onSubmit={submit}>
      <div className="panel-topline"><span>PAWLICE DEPARTMENT</span><span>CONFIDENTIAL-ish</span></div>
      <h2>Suspect particulars</h2><p className="field-note">Fields marked * are required.</p>
      <div className="field-grid">
        <label className="field"><span>NAME *</span><input name="name" value={form.name} onChange={update} required maxLength={100} /></label>
        <label className="field"><span>SPECIES *</span><input name="species" value={form.species} onChange={update} required maxLength={100} /></label>
        <label className="field"><span>BREED</span><input name="breed" value={form.breed} onChange={update} maxLength={100} /></label>
        <label className="field"><span>BIRTHDAY</span><input type="date" name="birthday" value={form.birthday} onChange={update} /></label>
        <label className="field field-full"><span>MUGSHOT IMAGE URL</span><input name="image_url" value={form.image_url} onChange={update} maxLength={2048} /></label>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><Link className="button button-quiet" to="/">Cancel</Link>
        <button className="button button-primary" disabled={submitting}>{submitting ? 'Opening file...' : 'Create case file →'}</button></div>
    </form><aside className="intake-preview"><div className="preview-label"><span>PREVIEW</span><span>FILE NO. PENDING</span></div>
      <PetImage src={form.image_url.trim()} name={form.name.trim() || 'this suspect'} />
      <div className="preview-caption"><strong>{form.name.trim() || 'Unknown suspect'}</strong><span>{form.species.trim() || 'Species unknown'}</span></div>
    </aside></div>
  </div>
}
