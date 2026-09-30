import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'

export default function AuthPage({ mode, onAuthenticated }) {
  const creatingAccount = mode === 'register'
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '', confirmPassword: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (creatingAccount && form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      const credentials = { email: form.email.trim(), password: form.password }
      const user = creatingAccount ? await api.register(credentials) : await api.login(credentials)
      onAuthenticated(user)
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-container auth-page">
      <div className="auth-intro">
        <p className="eyebrow">PAWLICE DEPARTMENT / AUTHORIZED PERSONNEL</p>
        <h1>{creatingAccount ? <>Open your <em>desk</em></> : <>Welcome <em>back</em></>}</h1>
        <p>{creatingAccount
          ? 'Create an account to keep your suspect files and incident reports together.'
          : 'Sign in to return to your private case files.'}</p>
        <span className="auth-stamp" aria-hidden="true">TOP<br />SECRET<br />(ISH)</span>
      </div>

      <form className="paper-panel auth-form" onSubmit={handleSubmit}>
        <div className="panel-topline"><span>{creatingAccount ? 'NEW ACCOUNT / FORM 00' : 'DESK ACCESS / FORM 00'}</span><span>PAWLICE REPORT</span></div>
        <h2>{creatingAccount ? 'Create account' : 'Sign in'}</h2>
        <label className="field">
          <span>EMAIL *</span>
          <input type="email" name="email" value={form.email} onChange={update} autoComplete="email" maxLength={255} required placeholder="you@example.com" />
        </label>
        <label className="field">
          <span>PASSWORD *</span>
          <input type="password" name="password" value={form.password} onChange={update} autoComplete={creatingAccount ? 'new-password' : 'current-password'} minLength={creatingAccount ? 8 : undefined} maxLength={128} required placeholder={creatingAccount ? 'At least 8 characters' : 'Your password'} />
        </label>
        {creatingAccount && <label className="field">
          <span>CONFIRM PASSWORD *</span>
          <input type="password" name="confirmPassword" value={form.confirmPassword} onChange={update} autoComplete="new-password" minLength={8} maxLength={128} required placeholder="Enter it again" />
        </label>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button button-primary auth-submit" type="submit" disabled={submitting}>
          {submitting ? 'Please wait...' : creatingAccount ? 'Create account →' : 'Sign in →'}
        </button>
        <p className="auth-switch">
          {creatingAccount ? 'Already have an account?' : 'New to the department?'}{' '}
          <Link to={creatingAccount ? '/login' : '/register'} state={location.state}>
            {creatingAccount ? 'Sign in' : 'Create an account'}
          </Link>
        </p>
      </form>
    </div>
  )
}
