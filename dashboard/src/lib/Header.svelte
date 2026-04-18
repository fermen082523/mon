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

<div class="sticky top-0 z-[60] bg-white/70 backdrop-blur-xl border-b border-slate-100/80 safe-top">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="flex justify-between items-center h-12 md:h-16">
			<!-- Logo -->
			<div class="flex items-center gap-2">
				<div class="h-7 w-7 bg-gradient-to-br from-indigo-600 to-violet-700 rounded-lg flex items-center justify-center text-white font-black shadow-md shadow-indigo-200">
					M
				</div>
				<h1 class="text-sm md:text-lg font-black text-slate-900 tracking-tight">RTV Live</h1>
			</div>

			<!-- User Menu -->
			<div class="flex items-center gap-3">
				{#if user}
					<div class="flex items-center gap-2 bg-slate-50 px-2 py-1 rounded-full border border-slate-100">
						<div class="h-5 w-5 bg-indigo-100 rounded-full flex items-center justify-center">
							<span class="text-[9px] font-black text-indigo-600 uppercase">
								{user.email?.charAt(0)}
							</span>
						</div>
						<span class="hidden md:block text-xs font-bold text-slate-600">{user.email?.split('@')[0]}</span>
						<button
							on:click={handleLogout}
							class="p-1 text-slate-400 hover:text-rose-500 transition-colors"
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17 16l4-4m0 0l-4-4m4 4H7" />
							</svg>
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
