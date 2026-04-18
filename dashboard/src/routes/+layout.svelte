<script lang="ts">
	import { onMount } from 'svelte';
	import { supabase, getUser } from '$lib/supabase';
	import { goto } from '$app/navigation';

	let user: any = null;

	onMount(async () => {
		const userData = await getUser();
		if (!userData) {
			goto('/');
		} else {
			user = userData;
		}

		const { data: { subscription } } = supabase.auth.onAuthStateChange(
			(event, session) => {
				if (!session) {
					goto('/');
				}
			}
		);

		return () => {
			subscription?.unsubscribe();
		};
	});
</script>

{#if user}
	<div class="min-h-screen bg-gray-50">
		<slot />
	</div>
{/if}
