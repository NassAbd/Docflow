import { useEffect, useState } from 'react';
import { getComplianceDashboard, getMyComplianceDashboard, listAlerts, listMyAlerts } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { AlertSeverity, AlertType, ComplianceDashboard, InconsistencyAlert } from '../types';

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  siret_mismatch: 'SIRET incohérent',
  amount_inconsistency: 'Montant incohérent',
  date_incoherence: 'Date incohérente',
  siren_format_invalid: 'Format SIREN invalide',
};

const SEVERITY_ICONS: Record<AlertSeverity, string> = {
  critique: '🔴',
  haute: '🟠',
  moyenne: '🟡',
  faible: '⚪',
};

function ComplianceRing({ value }: { value: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  const color = value >= 80 ? '#00d4aa' : value >= 50 ? '#ff9f43' : '#ff4d6d';

  return (
    <div className="compliance-ring">
      <svg viewBox="0 0 120 120" width="120" height="120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.5s ease' }}
        />
      </svg>
      <div className="compliance-ring-text">
        {value.toFixed(0)}%
        <small>conformes</small>
      </div>
    </div>
  );
}

export function CompliancePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [dashboard, setDashboard] = useState<ComplianceDashboard | null>(null);
  const [alerts, setAlerts] = useState<InconsistencyAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<AlertSeverity | 'all'>('all');

  useEffect(() => {
    Promise.all([
      isAdmin ? getComplianceDashboard() : getMyComplianceDashboard(),
      isAdmin ? listAlerts() : listMyAlerts(),
    ])
      .then(([dash, alts]) => {
        setDashboard(dash);
        setAlerts(alts);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAdmin]);

  const filteredAlerts =
    filterSeverity === 'all'
      ? alerts
      : alerts.filter((a) => a.severity === filterSeverity);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '4rem', justifyContent: 'center' }}>
        <div className="spinner" />
        <span className="loading-text">Chargement du dashboard…</span>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      <div className="page-header">
        <h1>🛡️ Dashboard Conformité</h1>
        <p>Analyse croisée des documents et détection automatique des incohérences.</p>
      </div>

      {/* KPI + Ring */}
      {dashboard && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap' }}>
            <ComplianceRing value={dashboard.taux_conformite} />
            <div className="stat-grid" style={{ flex: 1, margin: 0 }}>
              <div className="stat-card">
                <span className="stat-icon">📄</span>
                <span className="stat-value">{dashboard.total_documents}</span>
                <span className="stat-label">Total documents</span>
              </div>
              <div className="stat-card">
                <span className="stat-icon">✅</span>
                <span className="stat-value" style={{ color: 'var(--color-accent)' }}>
                  {dashboard.documents_conformes}
                </span>
                <span className="stat-label">Conformes</span>
              </div>
              <div className="stat-card">
                <span className="stat-icon">❌</span>
                <span className="stat-value" style={{ color: 'var(--color-danger)' }}>
                  {dashboard.documents_non_conformes}
                </span>
                <span className="stat-label">Non conformes</span>
              </div>
              <div className="stat-card">
                <span className="stat-icon">🔴</span>
                <span className="stat-value" style={{ color: 'var(--color-danger)' }}>
                  {dashboard.alertes_critiques}
                </span>
                <span className="stat-label">Critiques</span>
              </div>
              <div className="stat-card">
                <span className="stat-icon">🟠</span>
                <span className="stat-value" style={{ color: 'var(--color-warning)' }}>
                  {dashboard.alertes_hautes}
                </span>
                <span className="stat-label">Hautes</span>
              </div>
              <div className="stat-card">
                <span className="stat-icon">🟡</span>
                <span className="stat-value" style={{ color: 'var(--color-info)' }}>
                  {dashboard.alertes_moyennes}
                </span>
                <span className="stat-label">Moyennes</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <span className="section-title" style={{ marginBottom: 0 }}>Filtrer :</span>
        {(['all', 'critique', 'haute', 'moyenne', 'faible'] as const).map((sev) => (
          <button
            key={sev}
            id={`filter-${sev}`}
            className={`btn ${filterSeverity === sev ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setFilterSeverity(sev)}
            style={{ fontSize: '0.8rem', padding: '0.4rem 0.875rem' }}
          >
            {sev === 'all' ? 'Toutes' : (
              <>{SEVERITY_ICONS[sev as AlertSeverity]} {sev.charAt(0).toUpperCase() + sev.slice(1)}</>
            )}
          </button>
        ))}
      </div>

      {/* Alerts List */}
      {filteredAlerts.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon">🎉</span>
          <h3>Aucune alerte !</h3>
          <p>Tous les documents analysés sont cohérents.</p>
        </div>
      ) : (
        <div className="alerts-list">
          {filteredAlerts.map((alert) => (
            <div key={alert.id} className={`alert-item ${alert.severity}`}>
              <div className="alert-header">
                <span className={`badge badge-${alert.severity}`}>
                  {SEVERITY_ICONS[alert.severity]} {alert.severity}
                </span>
                <span className="badge badge-autre" style={{ textTransform: 'none' }}>
                  {ALERT_TYPE_LABELS[alert.alert_type]}
                </span>
                <span className="section-subtitle">
                  {alert.document_ids.length} document(s) impliqué(s)
                </span>
              </div>

              <p className="alert-description">{alert.description}</p>

              {alert.field_in_conflict && (
                <p className="alert-meta">
                  Champ : <code className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--color-primary)' }}>{alert.field_in_conflict}</code>
                  {alert.value_a && <> — Valeur A : <strong>{alert.value_a}</strong></>}
                  {alert.value_b && <> vs Valeur B : <strong>{alert.value_b}</strong></>}
                </p>
              )}

              {alert.suggestion && (
                <div className="alert-suggestion">
                  💡 <strong>Suggestion :</strong> {alert.suggestion}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
