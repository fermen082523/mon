<script lang="ts">
	import Header from '$lib/Header.svelte';
	import { onMount } from 'svelte';

	export let data: any;
</script>

<Header />

<div class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
	<slot />
</div>
