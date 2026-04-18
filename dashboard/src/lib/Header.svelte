<script lang="ts">
	import { signOut, getUser } from '$lib/supabase';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	let user: any = null;

	onMount(async () => {
		const userData = await getUser();
		user = userData;
	});

	async function handleLogout() {
		await signOut();
		goto('/');
	}
</script>

<div class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="flex justify-between items-center h-14 md:h-16">
			<!-- Logo / Titulo -->
			<div class="flex items-center gap-3">
				<div class="h-8 w-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-200">
					M
				</div>
				<div>
					<h1 class="text-base md:text-lg font-bold text-slate-900 leading-none">RTV Dashboard</h1>
					<p class="text-[10px] md:text-xs font-medium text-slate-500 uppercase tracking-wide">Live Monitor</p>
				</div>
			</div>

			<!-- User Menu -->
			<div class="flex items-center gap-2 md:gap-4">
				{#if user}
					<div class="hidden md:block text-right">
						<p class="text-sm font-semibold text-slate-900">{user.email?.split('@')[0]}</p>
						<div class="flex items-center justify-end gap-1">
							<span class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
							<p class="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Online</p>
						</div>
					</div>
					<div class="h-8 w-8 bg-slate-100 border border-slate-200 rounded-full flex items-center justify-center shadow-sm">
						<span class="text-xs font-bold text-indigo-600">
							{user.email?.charAt(0).toUpperCase()}
						</span>
					</div>
					<button
						on:click={handleLogout}
						class="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors group"
						title="Cerrar sesión"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
						</svg>
					</button>
				{/if}
			</div>
		</div>
	</div>
</div>
