export function formatPhone(raw) {
  if (!raw) return '';
  const d = String(raw).replace(/\D/g, '');
  if (d.length !== 10) return raw;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

export function stripPhone(val) {
  return val ? String(val).replace(/\D/g, '') : '';
}

export function ensureHttps(url) {
  if (!url) return url;
  const u = url.trim();
  if (!u) return u;
  if (!u.startsWith('http://') && !u.startsWith('https://')) return 'https://' + u;
  return u;
}

export function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch {
    return iso;
  }
}

export function validate(form) {
  const errs = {};
  if (form.phone) {
    if (stripPhone(form.phone).length !== 10) errs.phone = 'Must be 10 digits';
  }
  if (form.confidence_score !== null && form.confidence_score !== '' && form.confidence_score !== undefined) {
    const n = Number(form.confidence_score);
    if (isNaN(n) || n < 1 || n > 10) errs.confidence_score = 'Must be 1–10';
  }
  return errs;
}
