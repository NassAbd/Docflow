import { useEffect, useState } from 'react';
import { getCrmSuppliers, getMyCrmSuppliers, getSupplierDocuments, getMySupplierDocuments } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { GoldRecord, SupplierSummary } from '../types';

const TYPE_ICONS: Record<string, string> = {
  facture: '🧾',
  devis: '📋',
  attestation: '📜',
  autre: '📄',
};

export function CrmPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [suppliers, setSuppliers] = useState<SupplierSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierSummary | null>(null);
  const [supplierDocs, setSupplierDocs] = useState<GoldRecord[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  useEffect(() => {
    (isAdmin ? getCrmSuppliers() : getMyCrmSuppliers())
      .then(setSuppliers)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAdmin]);

  const openSupplier = async (supplier: SupplierSummary) => {
    setSelectedSupplier(supplier);
    setLoadingDocs(true);
    try {
      const docs = await (isAdmin ? getSupplierDocuments(supplier.siren) : getMySupplierDocuments(supplier.siren));
      setSupplierDocs(docs);
    } catch (err) {
      console.error('Error fetching supplier docs:', err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const closeSupplier = () => {
    setSelectedSupplier(null);
    setSupplierDocs([]);
  };

  const filtered = suppliers.filter(
    (s) =>
      s.nom.toLowerCase().includes(search.toLowerCase()) ||
      s.siren.includes(search)
  );

  const exportCsv = () => {
    const header = 'SIREN,Nom,Documents,Total TTC (€),Alertes,Types\n';
    const rows = filtered
      .map(
        (s) =>
          `${s.siren},"${s.nom}",${s.nombre_documents},${s.total_ttc},${s.a_des_alertes ? 'Oui' : 'Non'},"${s.types_documents.join('; ')}"`
      )
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crm_fournisseurs.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '4rem', justifyContent: 'center' }}>
        <div className="spinner" />
        <span className="loading-text">Chargement des fournisseurs…</span>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      <div className="page-header">
        <h1>CRM Fournisseurs</h1>
        <p>Vue consolidée de vos fournisseurs, regroupés par SIREN, avec montants cumulés et statut de conformité.</p>
      </div>

      {/* KPIs */}
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-icon">🏢</span>
          <span className="stat-value">{suppliers.length}</span>
          <span className="stat-label">Fournisseurs</span>
        </div>
        <div className="stat-card">
          <span className="stat-icon">📄</span>
          <span className="stat-value">{suppliers.reduce((s, x) => s + x.nombre_documents, 0)}</span>
          <span className="stat-label">Documents</span>
        </div>
        <div className="stat-card">
          <span className="stat-icon">💶</span>
          <span className="stat-value">
            {suppliers.reduce((s, x) => s + x.total_ttc, 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} €
          </span>
          <span className="stat-label">Total TTC</span>
        </div>
        <div className="stat-card">
          <span className="stat-icon">⚠️</span>
          <span className="stat-value" style={{ color: 'var(--color-warning)' }}>
            {suppliers.filter((s) => s.a_des_alertes).length}
          </span>
          <span className="stat-label">Avec alertes</span>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', alignItems: 'center' }}>
        <input
          id="supplier-search"
          type="text"
          placeholder="🔍 Rechercher par nom ou SIREN…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.625rem 1rem',
            color: 'var(--color-text)',
            fontSize: '0.9rem',
            fontFamily: 'inherit',
            outline: 'none',
            transition: 'border-color 200ms',
          }}
        />
        <button id="export-csv-btn" className="btn btn-ghost" onClick={exportCsv}>
          📥 Export CSV
        </button>
      </div>

      {/* Suppliers Grid */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon">🏭</span>
          <h3>Aucun fournisseur trouvé</h3>
          <p>Uploadez des documents pour voir apparaître les fournisseurs</p>
        </div>
      ) : (
        <div className="suppliers-grid">
          {filtered.map((s) => (
            <div 
              key={s.siren} 
              className={`supplier-card ${s.a_des_alertes ? 'has-alerts' : ''}`}
              onClick={() => openSupplier(s)}
              style={{ cursor: 'pointer' }}
            >
              <div>
                <div className="flex items-center gap-1" style={{ marginBottom: '0.25rem' }}>
                  <span className="supplier-name">{s.nom}</span>
                  {s.a_des_alertes && (
                    <span title="Alertes détectées" style={{ fontSize: '1rem' }}>⚠️</span>
                  )}
                </div>
                <div className="supplier-siren">SIREN : {s.siren}</div>
              </div>

              <div className="supplier-amount">
                {s.total_ttc.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €
              </div>

              <div className="flex gap-1" style={{ flexWrap: 'wrap' }}>
                {s.types_documents.map((t) => (
                  <span key={t} className={`badge badge-${t}`}>
                    {TYPE_ICONS[t]} {t}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">{s.nombre_documents} document(s)</span>
                {s.a_des_alertes ? (
                  <span className="badge badge-haute">⚠️ Alertes</span>
                ) : (
                  <span className="badge badge-curated">✅ Conforme</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Supplier Modal */}
      {selectedSupplier && (
        <div className="modal-overlay" onClick={closeSupplier}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{selectedSupplier.nom}</h2>
                <span className="text-sm text-muted font-mono">({selectedSupplier.siren})</span>
              </div>
              <button className="modal-close" onClick={closeSupplier}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="stat-grid" style={{ marginBottom: '2rem' }}>
                <div className="stat-card">
                  <span className="stat-label">Total Cumulé</span>
                  <span className="stat-value" style={{ fontSize: '1.5rem' }}>{selectedSupplier.total_ttc.toLocaleString('fr-FR')} €</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Documents</span>
                  <span className="stat-value" style={{ fontSize: '1.5rem' }}>{selectedSupplier.nombre_documents}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Conformité</span>
                  <span className={`badge ${selectedSupplier.a_des_alertes ? 'badge-haute' : 'badge-curated'}`} style={{ marginTop: '0.5rem' }}>
                    {selectedSupplier.a_des_alertes ? '⚠️ Alertes actives' : '✅ Dossier conforme'}
                  </span>
                </div>
              </div>

              <p className="section-title">📄 Historique des documents</p>
              
              {loadingDocs ? (
                <div className="flex items-center justify-center p-8 gap-2">
                  <div className="spinner" />
                  <span>Chargement des documents…</span>
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>N° Document</th>
                        <th>Montant TTC</th>
                        <th>Statut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {supplierDocs.sort((a, b) => new Date(b.curated_at).getTime() - new Date(a.curated_at).getTime()).map((doc) => (
                        <tr key={doc.document_id}>
                          <td className="text-sm">{new Date(doc.curated_at).toLocaleDateString('fr-FR')}</td>
                          <td>
                            <span className={`badge badge-${doc.document_type}`}>
                              {TYPE_ICONS[doc.document_type]} {doc.document_type}
                            </span>
                          </td>
                          <td className="font-mono text-sm">{doc.extraction.numero_document || '—'}</td>
                          <td style={{ fontWeight: 600 }}>{doc.extraction.montants.ttc?.toLocaleString('fr-FR')} €</td>
                          <td>
                            {doc.alerts.length > 0 ? (
                              <span className="badge badge-haute" title={`${doc.alerts.length} alerte(s)`}>⚠️ {doc.alerts.length}</span>
                            ) : (
                              <span className="badge badge-curated">✅ OK</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="modal-header" style={{ top: 'auto', bottom: 0, borderTop: '1px solid var(--color-border)', borderBottom: 'none' }}>
              <button className="btn btn-ghost w-full" onClick={closeSupplier}>Fermer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
