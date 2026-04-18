<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	
	export let ordenes: any[] = [];
	export let isMonitor: boolean = false;

	// Configuración de temas con colores CSS fijos (independientes de Tailwind)
	const themeMap: Record<string, { badge: string, border: string, bg: string, text: string }> = {
		PENDIENTE_SOLICITUD: {
			badge: '#4f46e5', // Indigo
			border: '#6366f1',
			bg: '#f5f7ff',
			text: '#ffffff'
		},
		SOLICITADA: {
			badge: '#f59e0b', // Amber
			border: '#fbbf24',
			bg: '#fffbeb',
			text: '#ffffff'
		},
		FINALIZADA: {
			badge: '#10b981', // Emerald
			border: '#34d399',
			bg: '#f0fdf4',
			text: '#ffffff'
		},
		ERROR: {
			badge: '#ef4444', // Red
			border: '#f87171',
			bg: '#fef2f2',
			text: '#ffffff'
		},
		ANULADA: {
			badge: '#64748b', // Slate
			border: '#94a3b8',
			bg: '#f8fafc',
			text: '#ffffff'
		}
	};

	function formatDate(date: string) {
		try {
			const d = new Date(date);
			return d.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' }) + 
				   ' ' + d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
		} catch (e) {
			return '-';
		}
	}
</script>

<div class="md:hidden space-y-3">
	{#each ordenes as orden (orden.local_id)}
		{@const normalizedEstado = (orden.estado || '').trim().toUpperCase()}
		{@const theme = themeMap[normalizedEstado] || themeMap.PENDIENTE_SOLICITUD}
		<div 
			in:fly={{ y: 20, duration: 400 }}
			class="relative p-4 rounded-3xl border-2 shadow-sm active:scale-95 transition-all duration-300"
			style="border-color: #f1f5f9; border-left-width: 8px; border-left-color: {theme.border}; background-color: {theme.bg};"
		>
			<div class="flex justify-between items-start mb-3">
				<div class="flex items-center gap-3">
					<!-- Placa (Simple) -->
					<div class="flex items-center justify-center h-8 w-16 bg-white border-2 border-slate-900 rounded-lg overflow-hidden shadow-sm">
						<span class="text-xs font-black text-slate-900 tracking-tight">{orden.placa}</span>
					</div>
					
					<div class="space-y-0.5">
						{#if !isMonitor}
							<p class="text-xs font-black text-slate-900 tracking-tight">{orden.numero_orden || 'Sin Orden'}</p>
						{/if}
						<p class="text-[9px] font-bold text-slate-500 uppercase tracking-wider">{formatDate(orden.updated_at)}</p>
					</div>
				</div>
			</div>
			
			<div class="flex items-center justify-between pt-3 border-t border-slate-900/5">
				<!-- Badge de Estado -->
				<span 
					class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest shadow-sm"
					style="background-color: {theme.badge}; color: {theme.text};"
				>
					{normalizedEstado.replace('_', ' ').split(' ')[0]}
				</span>
				
				{#if orden.etiqueta}
					<span class="px-2.5 py-0.5 bg-white border border-slate-200 text-slate-900 rounded text-[9px] font-black uppercase tracking-widest shadow-sm">
						{orden.etiqueta}
					</span>
				{/if}
			</div>
		</div>
	{/each}
</div>

<!-- Desktop Table View (Simplified with colors) -->
<div class="hidden md:block bg-white rounded-[2rem] shadow-sm border border-slate-100 overflow-hidden">
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-100">
			<thead class="bg-slate-50/50">
				<tr>
					<th class="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Vehículo</th>
					{#if !isMonitor}<th class="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Orden</th>{/if}
					<th class="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Estado</th>
					<th class="px-6 py-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Actualizado</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-50">
				{#each ordenes as orden (orden.local_id)}
					{@const normalizedEstado = (orden.estado || '').trim().toUpperCase()}
					{@const theme = themeMap[normalizedEstado] || themeMap.PENDIENTE_SOLICITUD}
					<tr class="hover:bg-slate-50/50 transition-colors group">
						<td class="px-6 py-4">
							<div class="h-8 w-16 bg-white border-2 border-slate-900 rounded-md flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
								<span class="text-xs font-black text-slate-900 tracking-tight">{orden.placa}</span>
							</div>
						</td>
						{#if !isMonitor}
							<td class="px-6 py-4 text-sm font-bold text-slate-600">{orden.numero_orden || '-'}</td>
						{/if}
						<td class="px-6 py-4">
							<span 
								class="inline-flex px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest shadow-sm"
								style="background-color: {theme.badge}; color: {theme.text};"
							>
								{normalizedEstado.replace('_', ' ')}
							</span>
						</td>
						<td class="px-6 py-4 text-xs font-bold text-slate-400">{formatDate(orden.updated_at)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

{#if ordenes.length === 0}
	<div class="bg-white rounded-[2.5rem] border-2 border-dashed border-slate-200 px-6 py-20 text-center">
		<p class="text-slate-400 font-black uppercase tracking-widest text-xs">Sin órdenes registradas</p>
	</div>
{/if}
