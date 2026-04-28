<script lang="ts">
	import { fade, fly } from 'svelte/transition';

	export let ordenes: any[] = [];
	export let isMonitor: boolean = false;
	export let isDigitador: boolean = false;

	let ordenSeleccionada: any = null;

	const themeMap: Record<string, { badge: string, border: string, bg: string, text: string }> = {
		PENDIENTE_SOLICITUD: {
			badge: '#4f46e5',
			border: '#6366f1',
			bg: '#f5f7ff',
			text: '#ffffff'
		},
		SOLICITADA: {
			badge: '#f59e0b',
			border: '#fbbf24',
			bg: '#fffbeb',
			text: '#ffffff'
		},
		FINALIZADA: {
			badge: '#10b981',
			border: '#34d399',
			bg: '#f0fdf4',
			text: '#ffffff'
		},
		ERROR: {
			badge: '#ef4444',
			border: '#f87171',
			bg: '#fef2f2',
			text: '#ffffff'
		},
		ANULADA: {
			badge: '#64748b',
			border: '#94a3b8',
			bg: '#f8fafc',
			text: '#ffffff'
		}
	};

	function formatDate(date: string) {
		try {
			const raw = (date || '').trim();
			if (!raw) return '-';
			const hasTimezone = /([zZ]|[+\-]\d{2}:\d{2})$/.test(raw);
			const normalized = hasTimezone ? raw : `${raw}Z`;
			const d = new Date(normalized);
			if (Number.isNaN(d.getTime())) return '-';
			const datePart = d.toLocaleDateString('es-ES', {
				month: 'short',
				day: 'numeric',
				timeZone: 'America/Bogota'
			});
			const timePart = d.toLocaleTimeString('es-ES', {
				hour: '2-digit',
				minute: '2-digit',
				timeZone: 'America/Bogota',
				hour12: false
			});
			return `${datePart} ${timePart}`;
		} catch (e) {
			return '-';
		}
	}

	function abrirDetalle(orden: any) {
		ordenSeleccionada = orden;
	}
</script>

<!-- Modal detalle de error -->
{#if ordenSeleccionada}
	<div
		transition:fade={{ duration: 150 }}
		class="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-4"
		on:click|self={() => ordenSeleccionada = null}
		role="dialog"
		aria-modal="true"
	>
		<div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"></div>
		<div
			in:fly={{ y: 30, duration: 250 }}
			class="relative w-full max-w-md bg-white rounded-[2.5rem] shadow-2xl p-6 space-y-4 border-2 border-slate-200"
		>
			<!-- Header -->
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="h-10 w-20 bg-white border-2 border-slate-900 rounded-lg flex items-center justify-center shadow-sm">
						<span class="text-sm font-black text-slate-900 tracking-tight">{ordenSeleccionada.placa}</span>
					</div>
					<div>
						{#if !isMonitor}
							<p class="text-xs font-black text-slate-700">{ordenSeleccionada.numero_orden || 'Sin Orden'}</p>
						{/if}
						<p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{formatDate(ordenSeleccionada.updated_at)}</p>
					</div>
				</div>
				<button
					on:click={() => ordenSeleccionada = null}
					class="h-8 w-8 flex items-center justify-center rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 transition-colors shadow-sm"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
					</svg>
				</button>
			</div>

			<!-- Error -->
			<div class="rounded-2xl p-4 space-y-2 {(ordenSeleccionada.estado === 'FINALIZADA' || ordenSeleccionada.resuelta_externamente) ? 'bg-amber-50 border border-amber-100' : 'bg-red-50 border border-red-100'}">
				<p class="text-[10px] font-black uppercase tracking-widest {(ordenSeleccionada.estado === 'FINALIZADA' || ordenSeleccionada.resuelta_externamente) ? 'text-amber-500' : 'text-red-400'}">
					{(ordenSeleccionada.estado === 'FINALIZADA' || ordenSeleccionada.resuelta_externamente) ? 'Historial de Incidencia (Ya resuelto)' : 'Detalle del error actual'}
				</p>
				{#if ordenSeleccionada.ultimo_error}
					<p class="text-sm font-bold leading-relaxed break-words {(ordenSeleccionada.estado === 'FINALIZADA' || ordenSeleccionada.resuelta_externamente) ? 'text-amber-700' : 'text-red-700'}">
						{ordenSeleccionada.ultimo_error}
					</p>
				{:else}
					<p class="text-sm italic {(ordenSeleccionada.estado === 'FINALIZADA' || ordenSeleccionada.resuelta_externamente) ? 'text-amber-400' : 'text-red-400'}">Sin detalle disponible.</p>
				{/if}
			</div>

			{#if ordenSeleccionada.resuelta_externamente}
				<div class="bg-blue-50 border border-blue-100 rounded-2xl p-4">
					<p class="text-[9px] font-black text-blue-500 uppercase tracking-widest mb-1">Nota del sistema</p>
					<p class="text-[11px] font-bold text-blue-700">Esta incidencia ya no requiere atención. La placa fue procesada exitosamente en otra entrada de hoy.</p>
				</div>
			{/if}

			{#if ordenSeleccionada.etiqueta}
				<div class="flex items-center justify-between px-2">
					<p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Etiqueta responsable</p>
					<span class="text-xs font-black text-indigo-600 uppercase bg-indigo-50 px-2 py-0.5 rounded-lg border border-indigo-100">{ordenSeleccionada.etiqueta}</span>
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- Mobile -->
<div class="md:hidden space-y-4">
	{#each ordenes as orden (orden.local_id)}
		{@const normalizedEstado = (orden.estado || '').trim().toUpperCase()}
		{@const theme = themeMap[normalizedEstado] || themeMap.PENDIENTE_SOLICITUD}
		{@const errorMsg = orden.error || orden.ultimo_error}
		<div
			in:fly={{ y: 20, duration: 400 }}
			out:fade={{ duration: 200 }}
			class="relative p-5 rounded-[2rem] border-2 shadow-md transition-all duration-300 hover:shadow-lg active:scale-[0.98]"
			style="border-color: #cbd5e1; border-left-width: 10px; border-left-color: {orden.resuelta_externamente ? '#2563eb' : (normalizedEstado === 'FINALIZADA' && orden.tuvo_error ? '#d97706' : theme.border)}; background-color: {theme.bg};"
		>
			<div class="flex justify-between items-start mb-4">
				<div class="flex items-center gap-4">
					<div class="flex items-center justify-center h-9 w-20 bg-white border-2 border-slate-900 rounded-xl overflow-hidden shadow-sm">
						<span class="text-sm font-black text-slate-900 tracking-tight">{orden.placa}</span>
					</div>

					<div class="space-y-0.5">
						{#if !isMonitor}
							<p class="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">Orden ANT</p>
							<p class="text-sm font-black text-slate-900 tracking-tight leading-none">{orden.numero_orden || 'Pendiente'}</p>
						{/if}
						<p class="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{formatDate(orden.updated_at)}</p>
					</div>
				</div>
			</div>

			<div class="flex items-center justify-between pt-4 border-t border-slate-900/5">
				<div class="flex items-center gap-2">
					{#if orden.resuelta_externamente}
						<span class="px-4 py-1.5 bg-blue-600 text-white rounded-full text-[9px] font-black uppercase tracking-[0.15em] shadow-lg shadow-blue-200 border-2 border-blue-400">
							Solucionada
						</span>
					{:else if normalizedEstado === 'FINALIZADA' && orden.tuvo_error}
						<span class="px-4 py-1.5 bg-amber-600 text-white rounded-full text-[9px] font-black uppercase tracking-[0.15em] shadow-lg shadow-amber-200 border-2 border-amber-400">
							Resuelta
						</span>
					{:else}
						<span
							class="px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.15em] shadow-sm"
							style="background-color: {theme.badge}; color: {theme.text};"
						>
							{normalizedEstado.replace('_', ' ')}
						</span>
					{/if}
				</div>

				{#if orden.etiqueta}
					<div class="flex items-center gap-2 px-3 py-1 bg-white/60 border border-slate-100 rounded-xl shadow-inner">
						<span class="text-[8px] font-black text-slate-400 uppercase tracking-widest">ID</span>
						<span class="text-[10px] font-black text-slate-900 uppercase">{orden.etiqueta}</span>
					</div>
				{/if}
			</div>

			{#if normalizedEstado === 'ERROR' || (normalizedEstado === 'FINALIZADA' && orden.tuvo_error)}
				<button
					on:click={() => abrirDetalle(orden)}
					class="mt-4 w-full flex items-center justify-between p-3 border-2 rounded-2xl transition-all active:scale-95 group {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'bg-blue-50 border-blue-100' : 'bg-red-50 border-red-100') : 'bg-amber-50 border-amber-100'}"
				>
					<div class="flex items-center gap-3 overflow-hidden">
						<div class="h-6 w-6 rounded-lg flex items-center justify-center shrink-0 {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'bg-blue-100 text-blue-600' : 'bg-red-100 text-red-600') : 'bg-amber-100 text-amber-600'}">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
								<path fill-rule="evenodd" d="{normalizedEstado === 'ERROR' ? 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z' : 'M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z'}" clip-rule="evenodd" />
							</svg>
						</div>
						<p class="text-[10px] font-bold truncate text-left {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'text-blue-600' : 'text-red-600') : 'text-amber-600'}">
							{normalizedEstado === 'FINALIZADA' ? 'Ver historial de incidencia' : (orden.resuelta_externamente ? 'Incidencia solucionada por re-ingreso' : (errorMsg || 'Ver incidencia'))}
						</p>
					</div>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 group-hover:translate-x-0.5 transition-transform {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'text-blue-300' : 'text-red-300') : 'text-amber-300'}" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
					</svg>
				</button>
			{/if}
		</div>
	{/each}
</div>

<!-- Desktop -->
<div class="hidden md:block bg-white rounded-[2.5rem] shadow-md border-2 border-slate-200 overflow-hidden">
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-50">
			<thead class="bg-slate-50/30">
				<tr>
					<th class="px-8 py-6 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Vehículo</th>
					{#if !isMonitor}<th class="px-8 py-6 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Orden ANT</th>{/if}
					{#if isDigitador}<th class="px-8 py-6 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Operador</th>{/if}
					<th class="px-8 py-6 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Estado Actual</th>
					<th class="px-8 py-6 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Cronología</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-slate-50">
				{#each ordenes as orden (orden.local_id)}
					{@const normalizedEstado = (orden.estado || '').trim().toUpperCase()}
					{@const theme = themeMap[normalizedEstado] || themeMap.PENDIENTE_SOLICITUD}
					{@const errorMsg = orden.error || orden.ultimo_error}
					<tr in:fade={{ duration: 200 }} class="hover:bg-slate-50/50 transition-colors group cursor-default">
						<td class="px-8 py-5">
							<div class="h-9 w-20 bg-white border-2 border-slate-900 rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 group-hover:shadow-md transition-all duration-300">
								<span class="text-xs font-black text-slate-900 tracking-tight">{orden.placa}</span>
							</div>
						</td>
						{#if !isMonitor}
							<td class="px-8 py-5">
								<span class="text-sm font-black text-slate-700 tracking-tight">{orden.numero_orden || '—'}</span>
							</td>
						{/if}
						{#if isDigitador}
							<td class="px-8 py-5">
								<div class="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-50 rounded-xl border border-slate-100">
									<span class="text-[9px] font-black text-indigo-600 uppercase tracking-widest">{orden.etiqueta || 'N/A'}</span>
								</div>
							</td>
						{/if}
						<td class="px-8 py-5">
							<div class="flex flex-col gap-2">
								<div class="flex items-center gap-2">
									{#if orden.resuelta_externamente}
										<span class="inline-flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-full text-[10px] font-black uppercase tracking-[0.15em] shadow-lg shadow-blue-100 border-2 border-blue-500 transition-transform hover:scale-105">
											<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
												<path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 100-2h-1a1 1 0 100 2h1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 10-2 0v1a1 1 0 102 0v-1zM8 16a1 1 0 100-2H7a1 1 0 100 2h1zM13 16a1 1 0 100-2h-1a1 1 0 100 2h1zM16.95 15.535a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707z" />
											</svg>
											Solucionada (Re-ingreso)
										</span>
									{:else if normalizedEstado === 'FINALIZADA' && orden.tuvo_error}
										<span class="inline-flex items-center gap-2 px-5 py-2 bg-amber-600 text-white rounded-full text-[10px] font-black uppercase tracking-[0.15em] shadow-lg shadow-amber-100 border-2 border-amber-500 transition-transform hover:scale-105">
											<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
											</svg>
											Resuelta tras error
										</span>
									{:else}
										<span
											class="inline-flex w-fit px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.1em] shadow-sm"
											style="background-color: {theme.badge}; color: {theme.text};"
										>
											{normalizedEstado.replace('_', ' ')}
										</span>
									{/if}
								</div>
								
								{#if normalizedEstado === 'ERROR' || (normalizedEstado === 'FINALIZADA' && orden.tuvo_error)}
									<button
										on:click={() => abrirDetalle(orden)}
										class="flex items-center gap-2 text-[10px] font-bold {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'text-blue-600 hover:text-blue-800' : 'text-red-600 hover:text-red-800') : 'text-amber-700 hover:text-amber-900'} max-w-[250px] text-left transition-all hover:translate-x-1 border-2 {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'border-blue-200 bg-blue-50' : 'border-red-200 bg-red-50') : 'border-amber-200 bg-amber-50'} rounded-xl px-3 py-1.5 shadow-sm"
									>
										<div class="h-1.5 w-1.5 rounded-full {normalizedEstado === 'ERROR' ? (orden.resuelta_externamente ? 'bg-blue-500' : 'bg-red-500') : 'bg-amber-500'}"></div>
										<span class="truncate">{normalizedEstado === 'FINALIZADA' ? 'Ver historial de incidencia' : (orden.resuelta_externamente ? 'Incidencia resuelta por re-ingreso' : (errorMsg || 'Ver incidencia'))}</span>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
											<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
										</svg>
									</button>
								{/if}
							</div>
						</td>
						<td class="px-8 py-5 text-xs font-bold text-slate-400 tabular-nums">{formatDate(orden.updated_at)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

{#if ordenes.length === 0}
	<div class="bg-white rounded-[2.5rem] border-2 border-dashed border-slate-200 px-6 py-20 text-center shadow-md">
		<p class="text-slate-400 font-black uppercase tracking-widest text-xs">Sin órdenes registradas</p>
	</div>
{/if}
