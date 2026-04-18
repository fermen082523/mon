<script lang="ts">
	import { onMount } from 'svelte';
	import { supabase, getUser } from '$lib/supabase';
	import StatCard from '$lib/StatCard.svelte';
	import OrdenesTable from '$lib/OrdenesTable.svelte';

	let stats = {
		pendiente: 0,
		solicitada: 0,
		finalizada: 0,
		error: 0,
		anulada: 0,
	};

	let ordenes: any[] = [];
	let loading = true;
	let filter = 'todas';
	let searchQuery = '';
	let isMonitor = false;

	// Filtrado reactivo: se activa con 2 o más dígitos
	$: filteredOrdenes = ordenes.filter(o => {
		if (searchQuery.length < 2) return true;
		const query = searchQuery.toLowerCase();
		return (o.placa?.toLowerCase().includes(query) || 
			   o.numero_orden?.toLowerCase().includes(query) ||
			   (o.etiqueta && o.etiqueta.toLowerCase().includes(query)));
	});

	async function loadStats() {
		try {
			const { data: allOrdenes, error } = await supabase
				.from('rtv_ordenes')
				.select('estado');

			if (error) throw error;

			stats = {
				pendiente: allOrdenes?.filter((o) => o.estado === 'PENDIENTE_SOLICITUD').length || 0,
				solicitada: allOrdenes?.filter((o) => o.estado === 'SOLICITADA').length || 0,
				finalizada: allOrdenes?.filter((o) => o.estado === 'FINALIZADA').length || 0,
				error: allOrdenes?.filter((o) => o.estado === 'ERROR').length || 0,
				anulada: allOrdenes?.filter((o) => o.estado === 'ANULADA').length || 0,
			};
		} catch (e) {
			console.error('Error loading stats:', e);
		}
	}

	async function loadOrdenes() {
		try {
			let query = supabase.from('rtv_ordenes').select('*').order('updated_at', { ascending: false });

			if (filter !== 'todas') {
				query = query.eq('estado', filter);
			}

			const { data, error } = await query;
			if (error) throw error;
			ordenes = data || [];
		} catch (e) {
			console.error('Error loading ordenes:', e);
		} finally {
			loading = false;
		}
	}

	function handleFilterChange(estado: string) {
		filter = estado;
		loadOrdenes();
	}

	onMount(async () => {
		const user = await getUser();
		if (user?.email) {
			const { data: appUser } = await supabase
				.from('app_users')
				.select('role')
				.ilike('username', user.email.split('@')[0])
				.single();
			isMonitor = appUser?.role === 'monitor';
		}

		loadStats();
		loadOrdenes();

		const subscription = supabase
			.channel('rtv_ordenes')
			.on('*', { event: 'INSERT,UPDATE,DELETE', schema: 'public', table: 'rtv_ordenes' }, () => {
				loadStats();
				loadOrdenes();
			})
			.subscribe();

		return () => {
			subscription.unsubscribe();
		};
	});
</script>

<svelte:head>
	<title>Dashboard - RTV</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-10 space-y-8 md:space-y-12">
	<!-- Title Section -->
	<div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
		<div>
			<h2 class="text-2xl md:text-4xl font-black text-slate-900 tracking-tight">Panel de Control</h2>
			<div class="flex items-center gap-2 mt-1">
				<span class="relative flex h-2 w-2">
					<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
					<span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
				</span>
				<p class="text-xs md:text-sm font-bold text-slate-500 uppercase tracking-widest">Monitoreo en vivo</p>
			</div>
		</div>
		
		<div class="hidden md:block">
			<button 
				on:click={() => { loadStats(); loadOrdenes(); }}
				class="inline-flex items-center px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-sm active:scale-95"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
				Actualizar
			</button>
		</div>
	</div>

	<!-- Statistics Grid -->
	<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-6">
		<StatCard label="En Cola" value={stats.pendiente} estado="pendiente" color="blue" />
		<StatCard label="Solicitadas" value={stats.solicitada} estado="solicitada" color="yellow" />
		<StatCard label="Finalizadas" value={stats.finalizada} estado="finalizada" color="green" />
		<StatCard label="Errores" value={stats.error} estado="error" color="red" />
		<StatCard label="Anuladas" value={stats.anulada} estado="anulada" color="purple" />
	</div>

	<!-- Filters & Content -->
	<div class="space-y-6">
		<div class="flex flex-col gap-6">
			<!-- Search Bar -->
			<div class="relative group">
				<div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
				</div>
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Buscar por placa, orden o etiqueta..."
					class="block w-full pl-11 pr-4 py-3.5 bg-white border border-slate-200 rounded-2xl text-sm font-medium placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
				/>
				{#if searchQuery}
					<button 
						on:click={() => searchQuery = ''}
						class="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
						</svg>
					</button>
				{/if}
			</div>

			<div class="flex flex-col gap-4">
				<div class="flex items-center justify-between">
					<h3 class="text-sm font-black text-slate-900 uppercase tracking-widest">Estado</h3>
					{#if filter !== 'todas' || searchQuery.length >= 2}
						<button 
							on:click={() => { filter = 'todas'; searchQuery = ''; loadOrdenes(); }}
							class="text-[10px] font-bold text-indigo-600 uppercase tracking-tighter hover:underline"
						>
							Limpiar Filtros
						</button>
					{/if}
				</div>
				
				<div class="flex overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0 no-scrollbar gap-2">
					{#each ['todas', 'PENDIENTE_SOLICITUD', 'SOLICITADA', 'FINALIZADA', 'ERROR'] as f}
						<button
							on:click={() => handleFilterChange(f)}
							class={`whitespace-nowrap px-5 py-2.5 rounded-xl text-xs font-bold transition-all border ${
								filter === f
									? 'bg-slate-900 text-white border-slate-900 shadow-md shadow-slate-200'
									: 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
							}`}
						>
							{f === 'todas' ? 'Todas' : f === 'PENDIENTE_SOLICITUD' ? 'En Cola' : f.charAt(0) + f.slice(1).toLowerCase()}
						</button>
					{/each}
				</div>
			</div>
		</div>

		<!-- Main Content Area -->
		<div class="relative min-h-[400px]">
			{#if loading}
				<div class="absolute inset-0 flex items-center justify-center bg-gray-50/50 backdrop-blur-[2px] z-10 rounded-2xl">
					<div class="flex flex-col items-center">
						<div class="h-10 w-10 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin"></div>
						<p class="text-xs font-bold text-slate-500 mt-4 uppercase tracking-widest">Sincronizando...</p>
					</div>
				</div>
			{/if}

			<div class={loading ? 'opacity-50 pointer-events-none' : ''}>
				<OrdenesTable ordenes={filteredOrdenes} {isMonitor} />
			</div>
		</div>
	</div>
</div>
