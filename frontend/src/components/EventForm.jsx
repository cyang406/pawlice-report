import { useState } from 'react'
import { eventTypes, eventTypeByValue } from '../eventTypes.js'

function localDateTime() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

export default function EventForm({ onAddEvent }) {
  const [form, setForm] = useState({
    event_type: 'INCIDENT', category: eventTypes[0].categories[0],
    description: '', severity: '3', event_time: localDateTime(),
  })
  const [submitting, setSubmitting] = useState(false)
  const [imageFile, setImageFile] = useState(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const type = eventTypeByValue[form.event_type]

  function update(event) {
    const { name, value } = event.target
    setForm((current) => name === 'event_type'
      ? { ...current, event_type: value, category: eventTypeByValue[value].categories[0], severity: '3' }
      : { ...current, [name]: value })
    setError('')
    setSuccess(false)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess(false)
    setSubmitting(true)
    try {
      await onAddEvent({
        event_type: form.event_type,
        category: form.category,
        description: form.description.trim(),
        event_time: new Date(form.event_time).toISOString(),
        ...(form.event_type === 'INCIDENT' ? { severity: Number(form.severity) } : {}),
      }, imageFile)
      setForm((current) => ({ ...current, description: '', event_time: localDateTime() }))
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
    <form className={`paper-panel report-form report-form--${form.event_type.toLowerCase().replace('_', '-')}`} onSubmit={handleSubmit}>
      <div className="panel-topline"><span>FORM 02 / PET JOURNAL</span><span>OFFICIAL BUSINESS</span></div>
      <div className="report-form-heading">
        <span className="report-icon" aria-hidden="true">{type.icon}</span>
        <div>
          <p className="eyebrow">{type.tag}</p>
          <h2>{type.heading}</h2>
        </div>
      </div>
      <p className="form-intro">{type.intro}</p>

      <div className="field-grid">
        <label className="field field-full">
          <span>EVENT TYPE *</span>
          <select name="event_type" value={form.event_type} onChange={update} disabled={submitting} required>
            {eventTypes.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className={`field ${form.event_type === 'INCIDENT' ? '' : 'field-full'}`}>
          <span>{type.categoryLabel} *</span>
          <select name="category" value={form.category} onChange={update} disabled={submitting} required>
            {type.categories.map((category) => <option key={category} value={category}>{category}</option>)}
          </select>
        </label>
        {form.event_type === 'INCIDENT' && <label className="field">
          <span>SEVERITY *</span>
          <select name="severity" value={form.severity} onChange={update} disabled={submitting} required>
            {[1, 2, 3, 4, 5].map((level) => <option key={level} value={level}>{level} / 5</option>)}
          </select>
        </label>}
        <label className="field field-full">
          <span>WHAT HAPPENED? *</span>
          <textarea name="description" value={form.description} onChange={update} disabled={submitting} required rows={4} placeholder="Add the details to the case file..." />
        </label>
        <label className="field field-full">
          <span>DATE & TIME *</span>
          <input type="datetime-local" name="event_time" value={form.event_time} onChange={update} disabled={submitting} required />
        </label>
        <label className="field field-full">
          <span>{form.event_type === 'INCIDENT' ? 'UPLOAD EVIDENCE PHOTO' : 'ATTACH PHOTO'}</span>
          <input key={fileInputKey} type="file" accept="image/*,.heic,.heif,.tif,.tiff,.avif" disabled={submitting} onChange={(event) => { setImageFile(event.target.files?.[0] || null); setSuccess(false) }} />
          <small>Optional photo from Photos or your files · 15 MB maximum.</small>
        </label>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {success && <p className="form-success" role="status">Entry added. The case file has been updated.</p>}
      <button className="button button-primary report-submit" type="submit" disabled={submitting}>
        {submitting ? 'Adding entry...' : form.event_type === 'INCIDENT' ? 'File incident report →' : 'Add to case file →'}
      </button>
    </form>
  )
}
