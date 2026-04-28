import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  collection, query, orderBy, limit, startAfter, where, getDocs, updateDoc, doc, getCountFromServer,
} from 'firebase/firestore';
import { db } from '../firebase';

const PAGE_SIZE = 50;

async function fetchPage(pageParam, filters = {}) {
  const constraints = [orderBy('found_at', 'desc'), limit(PAGE_SIZE)];
  if (filters.status)      constraints.push(where('status',      '==', filters.status));
  if (filters.territory)   constraints.push(where('territory',   '==', filters.territory));
  if (filters.source)      constraints.push(where('source',      '==', filters.source));
  if (filters.assigned_to) constraints.push(where('assigned_to', '==', filters.assigned_to));
  if (pageParam) constraints.push(startAfter(pageParam));
  const snap = await getDocs(query(collection(db, 'leads'), ...constraints));
  const leads = snap.docs
    .map((d) => ({ id: d.id, ...d.data() }))
    .filter((l) => l.is_valid_lead !== false);
  return {
    leads,
    lastDoc: snap.docs[snap.docs.length - 1] ?? null,
  };
}

export function useLeads(filters = {}) {
  return useInfiniteQuery({
    queryKey: ['leads', filters],
    queryFn: ({ pageParam }) => fetchPage(pageParam, filters),
    initialPageParam: null,
    getNextPageParam: (last) => last.lastDoc ?? undefined,
    enabled: Boolean(db),
  });
}

export function useTotalLeadCount() {
  return useQuery({
    queryKey: ['leads_total_count'],
    queryFn: async () => {
      const snap = await getCountFromServer(collection(db, 'leads'));
      return snap.data().count;
    },
    enabled: Boolean(db),
    staleTime: 5 * 60 * 1000,
  });
}

export function useSalesReps() {
  return useQuery({
    queryKey: ['sales_reps'],
    queryFn: async () => {
      const snap = await getDocs(collection(db, 'sales_reps'));
      return snap.docs.map((d) => ({ id: d.id, name: d.data().name ?? d.id }));
    },
    enabled: Boolean(db),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, changes }) => {
      await updateDoc(doc(db, 'leads', id), {
        ...changes,
        updated_at: new Date().toISOString(),
      });
      return id;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['leads'] }),
  });
}
