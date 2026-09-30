import PetImage from './PetImage.jsx'

const dayFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC', month: 'short', day: 'numeric', year: 'numeric',
})

function periodLabel(start, end) {
  // The API's end is exclusive; show the final included UTC day on the card.
  const lastDay = new Date(new Date(end).getTime() - 24 * 60 * 60 * 1000)
  return `${dayFormat.format(new Date(start))} — ${dayFormat.format(lastDay)}`
}

export default function ReportCard({ report, photoSrc, cardRef }) {
  const { stats } = report

  return (
    <article className="share-report" ref={cardRef} aria-label={`${report.period} Pawlice Report for ${report.pet_name}`}>
      <div className="share-report-topline"><span>PAWLICE DEPARTMENT</span><span>OFFICIAL PET ACTIVITY RECORD</span></div>
      <div className="share-report-body">
        <header className="share-report-header">
          <div>
            <p className="share-report-kicker">CASE FILE / {String(report.pet_id).padStart(4, '0')}</p>
            <h2>{report.period === 'weekly' ? 'Weekly' : 'Monthly'}<br /><em>Pawlice Report.</em></h2>
            <p className="share-report-period"><span>REPORTING PERIOD</span>{periodLabel(report.period_start, report.period_end)}</p>
          </div>
          <div className="share-report-mugshot">
            <PetImage src={photoSrc} name={report.pet_name} />
            <span>MUGSHOT / SUBJECT {String(report.pet_id).padStart(4, '0')}</span>
          </div>
        </header>

        <div className="share-report-subject"><span>SUBJECT ON FILE</span><strong>{report.pet_name}</strong><span>{stats.total_events} JOURNAL {stats.total_events === 1 ? 'ENTRY' : 'ENTRIES'}</span></div>

        <section className="share-report-section" aria-label="Activity summary">
          <div className="share-report-rule"><span>01 / ACTIVITY SUMMARY</span><span>THIS {report.period === 'weekly' ? 'WEEK' : 'MONTH'}</span></div>
          <div className="share-report-counts">
            <div className="share-count share-count-incident"><span>INCIDENTS</span><strong>{stats.incident_count}</strong><small>ON RECORD</small></div>
            <div className="share-count share-count-good"><span>GOOD CONDUCT</span><strong>{stats.good_conduct_count}</strong><small>COMMENDATIONS</small></div>
            <div className="share-count share-count-funny"><span>FUNNY MOMENTS</span><strong>{stats.funny_moment_count}</strong><small>NOTED</small></div>
            <div className="share-count share-count-wellness"><span>WELLNESS</span><strong>{stats.wellness_count}</strong><small>CHECKS</small></div>
          </div>
          <div className="share-report-facts">
            <div><span>TOP OFFENSE</span><strong>{stats.most_common_incident_category || 'No offenses recorded'}</strong></div>
            <div><span>AVERAGE MENACE LEVEL</span><strong>{stats.average_incident_severity == null ? 'N/A' : `${stats.average_incident_severity} / 5`}</strong></div>
            <div><span>MOST ACTIVE DAY</span><strong>{stats.most_active_event_day || 'No activity recorded'}</strong></div>
          </div>
        </section>

        <section className="share-report-narrative" aria-label="Officer notes">
          <div className="share-report-rule"><span>02 / OFFICER NOTES</span><span>FILED WITH AFFECTION</span></div>
          <p className="share-report-headline">{report.headline}</p>
          <div className="share-report-summary"><span>OFFICER'S SUMMARY</span><p>{report.officer_summary}</p></div>
          <div className="share-report-decisions">
            <div><span>VERDICT</span><p>{report.verdict}</p></div>
            <div><span>SENTENCE</span><p>{report.sentence}</p></div>
          </div>
        </section>
        <div className="share-report-signoff"><span>✦</span><span>PAWLICE DEPARTMENT<br /><small>ALL SUSPECTS ARE PRESUMED ADORABLE</small></span><span>FILE #{String(report.pet_id).padStart(4, '0')}</span></div>
      </div>
    </article>
  )
}
