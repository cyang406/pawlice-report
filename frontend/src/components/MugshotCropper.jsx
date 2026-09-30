import { useCallback, useEffect, useRef, useState } from 'react'
import Cropper from 'react-easy-crop'
import { api } from '../api/client.js'

const OUTPUT_SIZE = 800

function makeCroppedFile(imageUrl, area) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = OUTPUT_SIZE
        canvas.height = OUTPUT_SIZE
        const context = canvas.getContext('2d')
        if (!context) throw new Error('This browser could not crop the photo')
        context.drawImage(image, area.x, area.y, area.width, area.height, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE)
        canvas.toBlob(
          (blob) => blob ? resolve(new File([blob], 'mugshot.jpg', { type: 'image/jpeg' })) : reject(new Error('This browser could not save the crop')),
          'image/jpeg',
          0.9,
        )
      } catch (error) {
        reject(error)
      }
    }
    image.onerror = () => reject(new Error('The photo preview could not be opened'))
    image.src = imageUrl
  })
}

export default function MugshotCropper({ file, onSave, onCancel }) {
  const [imageUrl, setImageUrl] = useState('')
  const [preparing, setPreparing] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [cropPixels, setCropPixels] = useState(null)
  const cancelRef = useRef(null)

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    let active = true
    let objectUrl = ''
    setPreparing(true)
    setError('')
    setImageUrl('')
    setCrop({ x: 0, y: 0 })
    setZoom(1)
    setCropPixels(null)
    api.prepareMugshot(file)
      .then((blob) => {
        if (active) {
          objectUrl = URL.createObjectURL(blob)
          setImageUrl(objectUrl)
        }
      })
      .catch((err) => { if (active) setError(err.message) })
      .finally(() => { if (active) setPreparing(false) })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [file])

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === 'Escape' && !saving) onCancel()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onCancel, saving])

  const updateCropArea = useCallback((_, pixels) => setCropPixels(pixels), [])

  async function handleSave() {
    if (!imageUrl || !cropPixels || saving) return
    setSaving(true)
    setError('')
    try {
      await onSave(await makeCroppedFile(imageUrl, cropPixels))
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <div className="crop-overlay">
      <section className="crop-dialog paper-panel" role="dialog" aria-modal="true" aria-labelledby="crop-title">
        <div className="panel-topline"><span>PAWLICE PHOTO LAB</span><span>EXHIBIT A</span></div>
        <h2 id="crop-title">Crop the mugshot</h2>
        <p>Drag the photo to frame your suspect. Use the slider to zoom. The square shown here is what will appear on the case file.</p>
        {preparing ? (
          <div className="crop-loading" role="status"><span className="loading-mark" /> Preparing photo...</div>
        ) : imageUrl ? (
          <>
            <div className="crop-stage">
              <Cropper
                image={imageUrl}
                crop={crop}
                zoom={zoom}
                aspect={1}
                objectFit="cover"
                onCropChange={setCrop}
                onZoomChange={setZoom}
                onCropAreaChange={updateCropArea}
              />
            </div>
            <label className="crop-zoom">
              <span>ZOOM</span>
              <input type="range" min="1" max="3" step="0.01" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} />
            </label>
          </>
        ) : null}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="crop-actions">
          <button ref={cancelRef} className="button button-outline" type="button" onClick={onCancel} disabled={saving}>Cancel</button>
          <button className="button button-primary" type="button" onClick={handleSave} disabled={preparing || !cropPixels || saving}>
            {saving ? 'Saving crop...' : 'Use this crop →'}
          </button>
        </div>
      </section>
    </div>
  )
}
