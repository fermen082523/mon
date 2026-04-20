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
		loading = true;
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
			.on('postgres_changes', { event: '*', schema: 'public', table: 'rtv_ordenes' }, () => {
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

<div class="relative min-h-screen bg-[#f8fafc]">
	<!-- Background Color Accents -->
	<div class="fixed inset-0 overflow-hidden pointer-events-none">
		<div class="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-indigo-500/10 blur-[120px] rounded-full"></div>
		<div class="absolute bottom-0 right-0 w-[40%] h-[40%] bg-rose-500/10 blur-[120px] rounded-full"></div>
	</div>

	<div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-10 space-y-8 md:space-y-12">
		<!-- Header / Title -->
		<div class="flex items-center justify-between">
			<div class="space-y-1">
				<div class="flex items-center gap-2">
					<div class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
					<span class="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Sistema de Control</span>
				</div>
				<h2 class="text-3xl md:text-5xl font-black text-slate-900 tracking-tighter">Panel Central</h2>
			</div>
			
			<button 
				on:click={() => { loadStats(); loadOrdenes(); }}
				class="h-14 w-14 bg-white border border-slate-200 rounded-[1.5rem] flex items-center justify-center text-slate-700 hover:shadow-xl hover:border-indigo-200 hover:text-indigo-600 transition-all active:scale-90 shadow-sm"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
			</button>
		</div>

		<!-- Statistics Carousel -->
		<div class="flex overflow-x-auto pb-6 -mx-4 px-4 md:mx-0 md:px-0 no-scrollbar gap-5 md:grid md:grid-cols-5">
			<div class="min-w-[160px] md:min-w-0">
				<StatCard label="En Cola" value={stats.pendiente} estado="pendiente" color="blue" />
			</div>
			<div class="min-w-[160px] md:min-w-0">
				<StatCard label="Solicitadas" value={stats.solicitada} estado="solicitada" color="yellow" />
			</div>
			<div class="min-w-[160px] md:min-w-0">
				<StatCard label="Finalizadas" value={stats.finalizada} estado="finalizada" color="green" />
			</div>
			<div class="min-w-[160px] md:min-w-0">
				<StatCard label="Errores" value={stats.error} estado="error" color="red" />
			</div>
			<div class="min-w-[160px] md:min-w-0">
				<StatCard label="Anuladas" value={stats.anulada} estado="anulada" color="purple" />
			</div>
		</div>

		<!-- Content / Filters Sticky -->
		<div class="space-y-6">
			<div class="sticky top-[50px] md:top-[70px] z-50 py-4 -mx-4 px-4 md:mx-0 md:px-0 bg-[#f8fafc]/80 backdrop-blur-md">
				<div class="flex flex-col gap-5">
					<!-- Search -->
					<div class="relative group">
						<div class="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
							</svg>
						</div>
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Buscar placa o reporte..."
							class="block w-full pl-12 pr-6 py-4 bg-white border-2 border-slate-100 rounded-[1.5rem] text-sm font-black placeholder:text-slate-300 focus:outline-none focus:ring-8 focus:ring-indigo-500/5 focus:border-indigo-500 transition-all shadow-sm"
						/>
					</div>

					<!-- Filter Tabs -->
					<div class="flex overflow-x-auto no-scrollbar gap-3 py-2">
						{@const filters = [
							{ id: 'todas', label: 'Todos', color: '#64748b' },
							{ id: 'PENDIENTE_SOLICITUD', label: 'En Cola', color: '#4f46e5' },
							{ id: 'SOLICITADA', label: 'Solicitadas', color: '#f59e0b' },
							{ id: 'FINALIZADA', label: 'Finalizadas', color: '#10b981' },
							{ id: 'ERROR', label: 'Errores', color: '#ef4444' },
							{ id: 'ANULADA', label: 'Anuladas', color: '#a855f7' }
						]}
						
						{#each filters as f}
							<button
								on:click={() => handleFilterChange(f.id)}
								class="whitespace-nowrap px-6 py-3 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all border-2 active:scale-90"
								style="
									background-color: {filter === f.id ? f.color : 'white'};
									color: {filter === f.id ? 'white' : f.color};
									border-color: {f.color};
									box-shadow: {filter === f.id ? `0 10px 20px -5px ${f.color}66` : 'none'};
									opacity: {filter === f.id ? '1' : '0.7'};
								"
							>
								{f.label}
							</button>
						{/each}
					</div>
				</div>
			</div>

			<!-- List -->
			<div class="relative min-h-[400px]">
				{#if loading}
					<div class="absolute inset-0 flex items-center justify-center z-10">
						<div class="flex flex-col items-center gap-4">
							<div class="h-12 w-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
							<p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sincronizando</p>
						</div>
					</div>
				{/if}

				<div class={loading ? 'opacity-20 pointer-events-none blur-sm' : 'transition-all duration-500'}>
					<OrdenesTable ordenes={filteredOrdenes} {isMonitor} />
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.no-scrollbar::-webkit-scrollbar {
		display: none;
	}
	.no-scrollbar {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
</style>
