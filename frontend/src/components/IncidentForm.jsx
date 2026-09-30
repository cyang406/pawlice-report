import { useState } from 'react'

const categories = [
  'Food Theft', 'Property Damage', 'Sibling Assault', '3AM Zoomies',
  'Unauthorized Entry', 'Plant Destruction', 'Public Disturbance',
  'Furniture Damage', 'Suspicious Activity', 'Other',
]

function localDateTime() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

export default function IncidentForm({ onReport }) {
  const [form, setForm] = useState({
    category: categories[0], description: '', severity: '3',
    incident_time: localDateTime(), image_url: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [imageFile, setImageFile] = useState(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  function update(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    setSuccess(false)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess(false)
    setSubmitting(true)
    try {
      await onReport({
        category: form.category,
        description: form.description.trim(),
        severity: Number(form.severity),
        incident_time: new Date(form.incident_time).toISOString(),
        image_url: imageFile ? null : form.image_url.trim() || null,
      }, imageFile)
      setForm((current) => ({
        ...current, description: '', severity: '3',
        incident_time: localDateTime(), image_url: '',
      }))
      setImageFile(null)
      setFileInputKey((key) => key + 1)
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="paper-panel report-form" onSubmit={handleSubmit}>
      <div className="panel-topline"><span>FORM 02 / INCIDENT REPORT</span><span>OFFICIAL BUSINESS</span></div>
      <div className="report-form-heading">
        <span className="report-icon" aria-hidden="true">!</span>
        <div>
          <p className="eyebrow">WITNESS STATEMENT</p>
          <h2>Report a crime</h2>
        </div>
      </div>
      <p className="form-intro">Caught your suspect in the act? Add it to the permanent record.</p>

      <div className="field-grid">
        <label className="field">
          <span>CRIME CATEGORY *</span>
          <select name="category" value={form.category} onChange={update} required>
            {categories.map((category) => <option key={category} value={category}>{category}</option>)}
          </select>
        </label>
        <label className="field">
          <span>SEVERITY *</span>
          <select name="severity" value={form.severity} onChange={update} required>
            {[1, 2, 3, 4, 5].map((level) => <option key={level} value={level}>{level} / 5</option>)}
          </select>
        </label>
        <label className="field field-full">
          <span>WHAT HAPPENED? *</span>
          <textarea name="description" value={form.description} onChange={update} required rows={4} placeholder="Describe the alleged offense..." />
        </label>
        <label className="field">
          <span>DATE & TIME *</span>
          <input type="datetime-local" name="incident_time" value={form.incident_time} onChange={update} required />
        </label>
        <label className="field">
          <span>EVIDENCE IMAGE URL</span>
          <input name="image_url" value={form.image_url} onChange={update} maxLength={2048} placeholder="https://example.com/evidence.jpg" />
        </label>
        <label className="field field-full">
          <span>UPLOAD EVIDENCE PHOTO</span>
          <input key={fileInputKey} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { setImageFile(event.target.files?.[0] || null); setSuccess(false) }} />
          <small>Choose a photo from Photos or your files · 5 MB maximum. A selected file takes priority over a pasted URL.</small>
        </label>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {success && <p className="form-success" role="status">Incident filed. The case file has been updated.</p>}
      <button className="button button-primary report-submit" type="submit" disabled={submitting}>
        {submitting ? 'Filing report...' : 'File incident report →'}
      </button>
    </form>
  )
}
