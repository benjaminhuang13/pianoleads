import { useMemo, useState, useEffect } from 'react';
import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import { useLeads, useSalesReps, useTotalLeadCount } from './useLeads';
import { formatPhone, formatDate } from './utils';
import { LEAD_STATUS, SOURCE_TYPE, TERRITORY } from './constants';
import LeadModal from './LeadModal';
import { db } from '../firebase';
import './leads.css';

const col = createColumnHelper();

const STATUS_COLOR = {
  new: '#4a9eff',
  contacted: '#c8a96e',
  qualified: '#4caf76',
  closed: '#888',
  taken: '#e05555',
};

const MIN_COL = 60;

const COLUMNS = [
  col.accessor('studio_name', { header: 'Studio', size: 180, minSize: MIN_COL }),
  col.accessor('teacher_name', { header: 'Teacher', size: 150, minSize: MIN_COL }),
  col.accessor('phone', {
    header: 'Phone',
    size: 130,
    minSize: MIN_COL,
    cell: ({ getValue }) => formatPhone(getValue()) || '—',
    enableSorting: false,
  }),
  col.accessor('email', { header: 'Email', size: 190, minSize: MIN_COL }),
  col.accessor('status', {
    header: 'Status',
    size: 110,
    minSize: MIN_COL,
    cell: ({ getValue }) => {
      const v = getValue();
      return v
        ? <span className="status-pill" style={{ color: STATUS_COLOR[v] ?? 'inherit' }}>{v}</span>
        : '—';
    },
  }),
  col.accessor('assigned_to', { header: 'Assigned', size: 120, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('territory', { header: 'Territory', size: 120, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('source', { header: 'Source', size: 120, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('rating', { header: 'Rating', size: 75, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('review_count', { header: 'Reviews', size: 80, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('zip_code', { header: 'ZIP', size: 75, minSize: MIN_COL, cell: ({ getValue }) => getValue() ?? '—' }),
  col.accessor('found_at', {
    header: 'Found',
    size: 115,
    minSize: MIN_COL,
    cell: ({ getValue }) => formatDate(getValue()),
    sortingFn: 'datetime',
  }),
];

const SEARCH_FIELDS = ['studio_name', 'teacher_name', 'email', 'phone', 'address', 'zip_code', 'notes'];

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

const CSV_COLS = ['studio_name','teacher_name','phone','email','website','address','zip_code','status','territory','source','assigned_to','notes'];

function exportCSV(leads) {
  const rows = leads.map((l) => CSV_COLS.map((c) => JSON.stringify(l[c] ?? '')).join(','));
  const csv = [CSV_COLS.join(','), ...rows].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = 'leads.csv';
  a.click();
}

export default function LeadsPage() {
  const [searchRaw, setSearchRaw] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [territoryFilter, setTerritoryFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [assignedFilter, setAssignedFilter] = useState('');
  const [sorting, setSorting] = useState([{ id: 'found_at', desc: true }]);
  const [selectedLead, setSelectedLead] = useState(null);

  const search = useDebounce(searchRaw, 300);

  const { data: salesReps = [] } = useSalesReps();
  const { data: totalCount } = useTotalLeadCount();

  const dbFilters = useMemo(
    () => ({ status: statusFilter, territory: territoryFilter, source: sourceFilter, assigned_to: assignedFilter }),
    [statusFilter, territoryFilter, sourceFilter, assignedFilter],
  );

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError } = useLeads(dbFilters);

  const allLeads = useMemo(
    () => data?.pages.flatMap((p) => p.leads) ?? [],
    [data],
  );

  // text search is client-side (Firestore has no multi-field full-text search)
  const filtered = useMemo(() => {
    if (!search) return allLeads;
    const q = search.toLowerCase();
    return allLeads.filter((r) =>
      SEARCH_FIELDS.some((f) => String(r[f] ?? '').toLowerCase().includes(q)),
    );
  }, [allLeads, search]);

  const table = useReactTable({
    data: filtered,
    columns: COLUMNS,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualFiltering: true,
    columnResizeMode: 'onChange',
  });

  if (!db) return <div className="leads-message leads-error">Firebase not configured.</div>;
  if (isLoading) return <div className="leads-message">Loading leads…</div>;
  if (isError) return <div className="leads-message leads-error">Failed to load leads.</div>;

  return (
    <div className="leads-page">
      <div className="leads-toolbar">
        <div className="leads-title-row">
          <h2 className="leads-title">Leads</h2>
          <div className="leads-title-meta">
            <span className="leads-count">
              {filtered.length !== allLeads.length
                ? `${filtered.length} / ${allLeads.length}`
                : allLeads.length}{' '}
              {totalCount != null && ` out of ${totalCount.toLocaleString()} loaded`}
            </span>
            <button className="leads-export" onClick={() => exportCSV(filtered)}>Export CSV</button>
          </div>
        </div>
        <div className="leads-filters">
          <input
            className="leads-search"
            type="search"
            placeholder="Search name, email, phone, ZIP…"
            value={searchRaw}
            onChange={(e) => setSearchRaw(e.target.value)}
          />
          <select className="leads-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {LEAD_STATUS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="leads-select" value={territoryFilter} onChange={(e) => setTerritoryFilter(e.target.value)}>
            <option value="">All territories</option>
            {TERRITORY.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select className="leads-select" value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
            <option value="">All sources</option>
            {SOURCE_TYPE.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="leads-select" value={assignedFilter} onChange={(e) => setAssignedFilter(e.target.value)}>
            <option value="">All assignees</option>
            {salesReps.map((rep) => (
              <option key={rep.id} value={rep.name}>{rep.name}</option>
            ))}
          </select>
          {(statusFilter || territoryFilter || sourceFilter || assignedFilter || search) && (
            <button
              className="leads-clear"
              onClick={() => { setSearchRaw(''); setStatusFilter(''); setTerritoryFilter(''); setSourceFilter(''); setAssignedFilter(''); }}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="leads-table-wrap">
        <table className="leads-table" style={{ width: table.getTotalSize() }}>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    style={{ width: h.getSize(), position: 'relative' }}
                    className={h.column.getCanSort() ? 'col-sortable' : ''}
                    onClick={h.column.getToggleSortingHandler()}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {h.column.getIsSorted() === 'asc' && ' ↑'}
                    {h.column.getIsSorted() === 'desc' && ' ↓'}
                    <div
                      className={`col-resize-handle${h.column.getIsResizing() ? ' col-resize-active' : ''}`}
                      onMouseDown={h.getResizeHandler()}
                      onTouchStart={h.getResizeHandler()}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="leads-empty">No leads match.</td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="leads-row"
                  onClick={() => setSelectedLead(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} style={{ width: cell.column.getSize() }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {hasNextPage && (
        <div className="leads-load-more">
          <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? 'Loading…' : `Load more (${allLeads.length} loaded)`}
          </button>
        </div>
      )}

      {selectedLead && (
        <LeadModal
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onSaved={(updated) => setSelectedLead(updated)}
        />
      )}
    </div>
  );
}
