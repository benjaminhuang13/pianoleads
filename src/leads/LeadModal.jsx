import { useState, useEffect } from 'react';
import { useUpdateLead, useSalesReps } from './useLeads';
import { formatPhone, stripPhone, ensureHttps, validate, formatDate } from './utils';
import { LEAD_STATUS, SOURCE_TYPE, TERRITORY, READ_ONLY } from './constants';

function Toast({ msg, type, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3000);
    return () => clearTimeout(t);
  }, [onDismiss]);
  return <div className={`toast toast-${type}`}>{msg}</div>;
}

function Field({ label, children, error, fullWidth }) {
  return (
    <div className={`field${fullWidth ? ' field-full' : ''}${error ? ' field-has-error' : ''}`}>
      <label className="field-label">{label}</label>
      {children}
      {error && <span className="field-err">{error}</span>}
    </div>
  );
}

function normalizeValue(key, val) {
  if (key === 'phone') return stripPhone(val ?? '') || null;
  if (key === 'website') return ensureHttps(val?.trim() ?? '') || null;
  if (val === '' || val === undefined) return null;
  return val;
}

export default function LeadModal({ lead, onClose, onSaved }) {
  const [form, setForm] = useState({});
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState(null);
  const { mutateAsync, isPending } = useUpdateLead();
  const { data: salesReps = [], isError: repsError } = useSalesReps();

  useEffect(() => {
    setForm({
      ...lead,
      sources: lead.sources ?? [],
      domain_created: lead.domain_created ? lead.domain_created.slice(0, 10) : '',
    });
    setErrors({});
  }, [lead]);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  }

  function computeChanges() {
    const changes = {};
    for (const key of Object.keys(form)) {
      if (READ_ONLY.has(key)) continue;

      if (key === 'sources') {
        const a = [...(Array.isArray(form.sources) ? form.sources : [])].sort();
        const b = [...(Array.isArray(lead.sources) ? lead.sources : [])].sort();
        if (JSON.stringify(a) !== JSON.stringify(b)) changes.sources = form.sources;
        continue;
      }

      if (key === 'domain_created') {
        const cur = form.domain_created ? form.domain_created.slice(0, 10) : null;
        const orig = lead.domain_created ? lead.domain_created.slice(0, 10) : null;
        if (cur !== orig) changes.domain_created = cur ? new Date(cur).toISOString() : null;
        continue;
      }

      const current = normalizeValue(key, form[key]);
      const original = normalizeValue(key, lead[key]);
      if (current !== original) changes[key] = current;
    }
    return changes;
  }

  const hasChanges = Object.keys(form).length > 0 && Object.keys(computeChanges()).length > 0;

  async function handleSave() {
    const errs = validate(form);
    if (Object.keys(errs).length) { setErrors(errs); return; }

    const changes = computeChanges();

    if (Object.keys(changes).length === 0) { onClose(); return; }

    try {
      await mutateAsync({ id: lead.id, changes });
      const updated = { ...lead, ...changes, updated_at: new Date().toISOString() };
      setToast({ msg: 'Saved successfully', type: 'success' });
      onSaved(updated);
    } catch (err) {
      setToast({ msg: `Save failed: ${err.message}`, type: 'error' });
    }
  }

  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-drawer" role="dialog" aria-modal="true">
        <div className="modal-header">
          <div>
            <h3 className="modal-title">{form.studio_name || form.teacher_name || 'Lead'}</h3>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="modal-body">
          <section className="modal-section">
            <h4 className="modal-section-title">Metadata</h4>
            <div className="field-grid">
              <Field label="Rating"><span>{lead.rating ?? '—'}</span></Field>
              <Field label="Reviews"><span>{lead.review_count ?? '—'}</span></Field>
              <Field label="Most recent review"><span>{formatDate(lead.most_recent_review)}</span></Field>
              <Field label="Photos"><span>{lead.photo_count ?? '—'}</span></Field>
              <Field label="Found at"><span>{formatDate(lead.found_at)}</span></Field>
              <Field label="Updated at"><span>{formatDate(lead.updated_at)}</span></Field>
            </div>
          </section>

          <section className="modal-section">
            <h4 className="modal-section-title">Contact</h4>
            <div className="field-grid">
              <Field label="Studio name">
                <input value={form.studio_name ?? ''} onChange={(e) => set('studio_name', e.target.value)} />
              </Field>
              <Field label="Teacher name">
                <input value={form.teacher_name ?? ''} onChange={(e) => set('teacher_name', e.target.value)} />
              </Field>
              <Field label="Phone" error={errors.phone}>
                <input
                  value={form.phone ? formatPhone(form.phone) : ''}
                  onChange={(e) => set('phone', e.target.value)}
                  placeholder="(555) 555-5555"
                />
              </Field>
              <Field label="Email">
                <input type="email" value={form.email ?? ''} onChange={(e) => set('email', e.target.value)} />
              </Field>
              <Field label="Website">
                <input value={form.website ?? ''} onChange={(e) => set('website', e.target.value)} placeholder="https://" />
              </Field>
              <Field label="Address">
                <input value={form.address ?? ''} onChange={(e) => set('address', e.target.value)} />
              </Field>
              <Field label="ZIP code">
                <input value={form.zip_code ?? ''} onChange={(e) => set('zip_code', e.target.value)} />
              </Field>
            </div>
          </section>

          <section className="modal-section">
            <h4 className="modal-section-title">Classification</h4>
            <div className="field-grid">
              <Field label="Assigned to" error={repsError ? 'Could not load reps (check Firestore rules)' : undefined}>
                <select value={form.assigned_to ?? ''} onChange={(e) => set('assigned_to', e.target.value)}>
                  <option value="">—</option>
                  {salesReps.map((rep) => (
                    <option key={rep.id} value={rep.name}>{rep.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Status">
                <select value={form.status ?? ''} onChange={(e) => set('status', e.target.value)}>
                  {LEAD_STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Territory">
                <select value={form.territory ?? ''} onChange={(e) => set('territory', e.target.value)}>
                  <option value="">—</option>
                  {TERRITORY.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <Field label="Primary source">
                <select value={form.source ?? ''} onChange={(e) => set('source', e.target.value)}>
                  <option value="">—</option>
                  {SOURCE_TYPE.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Confidence score" error={errors.confidence_score}>
                <input
                  type="number" min={1} max={10}
                  value={form.confidence_score ?? ''}
                  onChange={(e) => set('confidence_score', e.target.value === '' ? null : Number(e.target.value))}
                />
              </Field>
              <Field label="Duplicate of">
                <input value={form.duplicate_of ?? ''} onChange={(e) => set('duplicate_of', e.target.value)} placeholder="Lead UUID" />
              </Field>
              <Field label="Sources (all that apply)" fullWidth>
                <div className="sources-wrap">
                  {SOURCE_TYPE.map((s) => (
                    <label key={s} className="source-check">
                      <input
                        type="checkbox"
                        checked={(form.sources ?? []).includes(s)}
                        onChange={(e) => {
                          const prev = form.sources ?? [];
                          set('sources', e.target.checked ? [...prev, s] : prev.filter((x) => x !== s));
                        }}
                      />
                      {s}
                    </label>
                  ))}
                </div>
              </Field>
            </div>
          </section>

          <section className="modal-section">
            <h4 className="modal-section-title">Domain</h4>
            <div className="field-grid">
              <Field label="Domain created">
                <input
                  type="date"
                  value={form.domain_created ?? ''}
                  onChange={(e) => set('domain_created', e.target.value)}
                />
              </Field>
              <Field label="Domain age (days)">
                <input
                  type="number"
                  value={form.domain_age_days ?? ''}
                  onChange={(e) => set('domain_age_days', e.target.value === '' ? null : Number(e.target.value))}
                />
              </Field>
            </div>
          </section>

          <section className="modal-section">
            <h4 className="modal-section-title">Notes</h4>
            <textarea
              className="notes-input"
              value={form.notes ?? ''}
              onChange={(e) => set('notes', e.target.value)}
              rows={5}
              placeholder="Free-form notes…"
            />
          </section>

          <section className="modal-section">
            <h4 className="modal-section-title">Validation</h4>
            <div className="field-grid">
              <Field label="Valid lead (if you make this no, it will be hidden)">
                <select
                  value={form.is_valid_lead === true ? 'true' : form.is_valid_lead === false ? 'false' : ''}
                  onChange={(e) => set('is_valid_lead', e.target.value === 'true' ? true : e.target.value === 'false' ? false : null)}
                >
                  <option value="">—</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </Field>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={isPending} style={!hasChanges ? { opacity: 0.35, cursor: 'default' } : undefined}>
            {isPending ? 'Saving…' : 'Save changes'}
          </button>
        </div>

        {toast && <Toast msg={toast.msg} type={toast.type} onDismiss={() => setToast(null)} />}
      </div>
    </>
  );
}
