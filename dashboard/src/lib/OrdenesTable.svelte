<script lang="ts">
	export let ordenes: any[] = [];
	export let isMonitor: boolean = false;

	const estadoColor: Record<string, string> = {
		PENDIENTE_SOLICITADA: 'bg-amber-100 text-amber-700 border-amber-200',
		PENDIENTE_SOLICITUD: 'bg-blue-100 text-blue-700 border-blue-200',
		SOLICITADA: 'bg-indigo-100 text-indigo-700 border-indigo-200',
		FINALIZADA: 'bg-emerald-100 text-emerald-700 border-emerald-200',
		ERROR: 'bg-rose-100 text-rose-700 border-rose-200',
		ANULADA: 'bg-slate-100 text-slate-600 border-slate-200',
	};

	function formatDate(date: string) {
		const d = new Date(date);
		return d.toLocaleDateString('es-ES', {
			month: 'short',
			day: 'numeric',
		}) + ' ' + d.toLocaleTimeString('es-ES', {
			hour: '2-digit',
			minute: '2-digit',
		});
	}
</script>

<!-- Desktop Table View -->
<div class="hidden md:block bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-slate-200">
			<thead class="bg-slate-50/50">
				<tr>
					<th class="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Vehículo</th>
					{#if !isMonitor}<th class="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Orden ANT</th>{/if}
					<th class="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Estado</th>
					{#if !isMonitor}<th class="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Etiqueta</th>{/if}
					<th class="px-6 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Última Act.</th>
				</tr>
			</thead>
			<tbody class="bg-white divide-y divide-slate-100">
				{#each ordenes as orden (orden.local_id)}
					<tr class="hover:bg-slate-50/50 transition-colors group">
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="flex items-center">
								<div class="h-8 w-8 rounded bg-slate-100 flex items-center justify-center mr-3 group-hover:bg-white transition-colors">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
									</svg>
								</div>
								<span class="text-sm font-bold text-slate-900 tracking-tight">{orden.placa}</span>
							</div>
						</td>
					{#if !isMonitor}<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600 font-medium">{orden.numero_orden || '-'}</td>{/if}
					<td class="px-6 py-4 whitespace-nowrap">
						<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${estadoColor[orden.estado] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
							<span class="h-1.5 w-1.5 rounded-full bg-current mr-1.5 opacity-50"></span>
							{orden.estado.replace('_', ' ')}
						</span>
					</td>
					{#if !isMonitor}<td class="px-6 py-4 whitespace-nowrap">
						{#if orden.etiqueta}
							<span class="inline-flex items-center px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
								{orden.etiqueta}
							</span>
						{:else}
							<span class="text-slate-300 text-xs">-</span>
						{/if}
					</td>{/if}
						<td class="px-6 py-4 whitespace-nowrap text-xs text-slate-500 font-medium">{formatDate(orden.updated_at)}</td>
					</tr>
				{/each}
			</tbody>
		<script lang="ts">
			import { fade, fly } from 'svelte/transition';
			import { flip } from 'svelte/animate';

			export let ordenes: any[] = [];
			export let isMonitor: boolean = false;
		...
		<!-- Mobile Card View -->
		<div class="md:hidden space-y-4">
			{#each ordenes as orden (orden.local_id)}
				<div 
					in:fly={{ y: 20, duration: 400 }}
					class="bg-white p-5 rounded-[2rem] border border-slate-200 shadow-sm active:scale-[0.97] transition-all duration-300"
				>
					<div class="flex justify-between items-start mb-4">
						<div class="flex items-center gap-3">
							<!-- License Plate Styled Icon -->
							<div class="flex flex-col items-center justify-center h-10 w-16 bg-slate-100 border-2 border-slate-900 rounded-lg overflow-hidden shadow-sm">
								<div class="h-2 w-full bg-indigo-600"></div>
								<span class="text-[11px] font-black text-slate-900 leading-none py-1.5">{orden.placa}</span>
							</div>
							<div class="space-y-0.5">
								{#if !isMonitor}
									<p class="text-xs font-black text-slate-900 tracking-tight">{orden.numero_orden || 'S/O'}</p>
								{/if}
								<div class="flex items-center gap-1.5 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									{formatDate(orden.updated_at)}
								</div>
							</div>
						</div>
						<span class={`px-3 py-1 rounded-full text-[10px] font-black tracking-widest border shadow-sm ${estadoColor[orden.estado] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
							{orden.estado.split('_')[0]}
						</span>
					</div>

					<div class="flex items-center justify-between pt-4 border-t border-slate-50">
						<div class="flex flex-wrap gap-2">
							{#if !isMonitor && orden.etiqueta}
								<span class="px-2.5 py-1 bg-indigo-600 text-white rounded-lg text-[9px] font-black uppercase tracking-widest shadow-md shadow-indigo-100">
									{orden.etiqueta}
								</span>
							{/if}
						</div>
						<div class="text-[10px] font-bold text-slate-300 bg-slate-50 px-2 py-0.5 rounded-full tracking-tighter">#{orden.local_id.toString().slice(-4)}</div>
					</div>
				</div>
			{/each}
		</div>


{#if ordenes.length === 0}
	<div class="bg-white rounded-2xl border border-dashed border-slate-300 px-6 py-12 text-center">
		<div class="h-12 w-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
			<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
			</svg>
		</div>
		<p class="text-slate-500 font-medium">No hay órdenes para mostrar</p>
	</div>
{/if}
