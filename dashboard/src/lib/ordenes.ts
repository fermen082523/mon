import { supabase } from './supabase';

export async function fetchOrdenes() {
  const { data, error } = await supabase
    .from('rtv_ordenes')
    .select('*')
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data || [];
}

export async function fetchOrdenesByEstado(estado: string) {
  const { data, error } = await supabase
    .from('rtv_ordenes')
    .select('*')
    .eq('estado', estado)
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data || [];
}

export async function fetchOrdenesByEtiqueta(etiqueta: string) {
  const { data, error } = await supabase
    .from('rtv_ordenes')
    .select('*')
    .eq('etiqueta', etiqueta)
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data || [];
}

export async function fetchAuditoriaByOrden(ordenId: number) {
  const { data, error } = await supabase
    .from('rtv_auditoria')
    .select('*')
    .eq('orden_local_id', ordenId)
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data || [];
}

export async function fetchResumen() {
  const { data: ordenes, error } = await supabase
    .from('rtv_ordenes')
    .select('estado, etiqueta, count()')
    .then(({ data, error }) => {
      if (error) throw error;
      return { data: data || [], error };
    });
  
  return {
    pendiente: ordenes.filter((o: any) => o.estado === 'PENDIENTE_SOLICITUD').length,
    solicitada: ordenes.filter((o: any) => o.estado === 'SOLICITADA').length,
    finalizada: ordenes.filter((o: any) => o.estado === 'FINALIZADA').length,
    error: ordenes.filter((o: any) => o.estado === 'ERROR').length,
    anulada: ordenes.filter((o: any) => o.estado === 'ANULADA').length,
  };
}
