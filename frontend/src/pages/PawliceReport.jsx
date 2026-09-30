import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toBlob } from 'html-to-image'
import { api } from '../api/client.js'
import ReportCard from '../components/ReportCard.jsx'

function photoAsDataUrl(url, signal) {
  return fetch(url, { credentials: 'same-origin', signal })
    .then((response) => {
      if (!response.ok) throw new Error('Photo unavailable')
      return response.blob()
    })
    .then((blob) => {
      if (!blob.type.startsWith('image/')) throw new Error('Not an image')
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    })
}

function reportFilename(name, period) {
  const slug = name.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'pet'
  return `${slug}-pawlice-${period}-report.png`
}

export default function PawliceReport() {
  const { id } = useParams()
  const cardRef = useRef(null)
  const [pet, setPet] = useState(null)
  const [petLoading, setPetLoading] = useState(true)
  const [petError, setPetError] = useState('')
  const [period, setPeriod] = useState('weekly')
  const [report, setReport] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [photoSrc, setPhotoSrc] = useState(null)
  const [photoLoading, setPhotoLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')

  useEffect(() => {
    let active = true
    setPet(null)
    setReport(null)
    setPhotoSrc(null)
    setPetLoading(true)
    setPetError('')
    api.getPet(id)
      .then((result) => { if (active) setPet(result) })
      .catch((err) => { if (active) setPetError(err.message) })
      .finally(() => { if (active) setPetLoading(false) })
    return () => { active = false }
  }, [id])

  useEffect(() => {
    let active = true
    setPhotoSrc(null)
    if (!pet?.image_url) {
      setPhotoLoading(false)
      return
    }
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 8000)
    setPhotoLoading(true)
    photoAsDataUrl(pet.image_url, controller.signal)
      .then((src) => { if (active) setPhotoSrc(src) })
      .catch(() => { if (active) setPhotoSrc(null) })
      .finally(() => { clearTimeout(timeout); if (active) setPhotoLoading(false) })
    return () => { active = false; controller.abort(); clearTimeout(timeout) }
  }, [pet?.image_url])

  async function generate() {
    setGenerateError('')
    setDownloadError('')
    setGenerating(true)
    try {
      setReport(await api.generateReport(id, period))
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  async function download() {
    if (!cardRef.current || !report) return
    setDownloadError('')
    setDownloading(true)
    try {
      await document.fonts.ready
      const blob = await toBlob(cardRef.current, { pixelRatio: 2, backgroundColor: '#fffdf7' })
      if (!blob) throw new Error('Could not create the PNG file.')
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = reportFilename(report.pet_name, report.period)
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      setDownloadError('The report image could not be created. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  if (petLoading) return <div className="page-container profile-loading" role="status"><span className="loading-mark" /> Retrieving case file...</div>
  if (petError || !pet) return <div className="page-container missing-page" role="alert"><p className="eyebrow">REPORT UNAVAILABLE</p><h1>Case file not found.</h1><p>{petError}</p><Link className="button button-outline" to="/">Back to suspects</Link></div>

  return (
    <div className="page-container report-page">
      <Link className="back-link" to={`/pets/${id}`}>← Back to {pet.name}'s profile</Link>
      <div className="report-page-intro">
        <div><p className="eyebrow">PAWLICE DEPARTMENT / REPORT DESK</p><h1>The <em>Pawlice Report.</em></h1><p>A little paperwork for a very important suspect. Choose a period, then file the report.</p></div>
      </div>

      <div className="report-controls paper-panel">
        <fieldset disabled={generating}>
          <legend>REPORTING PERIOD</legend>
          <label className={period === 'weekly' ? 'selected' : ''}><input type="radio" name="report-period" value="weekly" checked={period === 'weekly'} onChange={() => { setPeriod('weekly'); setReport(null); setGenerateError('') }} /> Weekly Report</label>
          <label className={period === 'monthly' ? 'selected' : ''}><input type="radio" name="report-period" value="monthly" checked={period === 'monthly'} onChange={() => { setPeriod('monthly'); setReport(null); setGenerateError('') }} /> Monthly Report</label>
        </fieldset>
        <button type="button" className="button button-primary" onClick={generate} disabled={generating}>{generating ? 'Filing report...' : report ? 'Refresh Report →' : 'Generate Report →'}</button>
      </div>
      {generateError && <p className="form-error" role="alert">{generateError}</p>}

      {generating && !report && <div className="report-wait" role="status"><span className="loading-mark" /> The Pawlice desk is preparing this case file...</div>}
      {!report && !generating && <div className="report-placeholder"><span aria-hidden="true">✦</span><h2>A report is ready to be filed.</h2><p>Generate a weekly or monthly record for {pet.name}. Even a quiet period deserves official paperwork.</p></div>}

      {report && <>
        <div className="report-preview-label"><span>REPORT PREVIEW</span><span>READY FOR THE RECORD</span></div>
        <ReportCard report={report} photoSrc={photoSrc} cardRef={cardRef} />
        <div className="report-download-row">
          <p>{photoLoading ? 'Preparing the mugshot for export...' : 'This image includes only the report card.'}</p>
          <button type="button" className="button button-primary" onClick={download} disabled={downloading || photoLoading || generating}>{downloading ? 'Preparing PNG...' : 'Download Report ↓'}</button>
        </div>
        {downloadError && <p className="form-error" role="alert">{downloadError}</p>}
      </>}
    </div>
  )
}
