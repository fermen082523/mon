<script lang="ts">
	import '../app.css';
	import { signIn } from '$lib/supabase';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getUser } from '$lib/supabase';

	let email = '';
	let password = '';
	let loading = false;
	let error = '';
	let checkingAuth = true;

	onMount(async () => {
		const user = await getUser();
		if (user) {
			goto('/dashboard');
		}
		checkingAuth = false;
	});

	async function handleLogin() {
		loading = true;
		error = '';

		const { error: signInError } = await signIn(email, password);

		if (signInError) {
			error = signInError.message;
			loading = false;
		} else {
			goto('/dashboard');
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !loading) {
			handleLogin();
		}
	}
</script>

<svelte:head>
	<title>Iniciar Sesión - MONITOR Dashboard</title>
</svelte:head>

{#if checkingAuth}
	<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
		<div class="text-center">
			<div class="inline-flex items-center justify-center h-12 w-12 rounded-md bg-indigo-600 text-white mb-4">
				<svg class="h-6 w-6 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
				</svg>
			</div>
			<p class="text-gray-600">Verificando sesión...</p>
		</div>
	</div>
{:else}
	<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
		<div class="w-full max-w-md">
			<div class="bg-white rounded-lg shadow-xl p-8">
				<!-- Header -->
				<div class="text-center mb-8">
					<div class="inline-flex items-center justify-center h-12 w-12 rounded-md bg-indigo-600 text-white mb-4">
						<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
					<h1 class="text-2xl font-bold text-gray-900">MONITOR Dashboard</h1>
					<p class="text-gray-600 text-sm mt-1">Monitoreo de inspecciones vehiculares</p>
				</div>

				<!-- Login Form -->
				<form on:submit|preventDefault={handleLogin}>
					<!-- Email -->
					<div class="mb-4">
						<label for="email" class="block text-sm font-medium text-gray-700 mb-2">
							Correo electrónico
						</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							placeholder="tu@email.com"
							disabled={loading}
							on:keydown={handleKeydown}
							class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none disabled:opacity-50 disabled:cursor-not-allowed"
							required
						/>
					</div>

					<!-- Password -->
					<div class="mb-6">
						<label for="password" class="block text-sm font-medium text-gray-700 mb-2">
							Contraseña
						</label>
						<input
							id="password"
							type="password"
							bind:value={password}
							placeholder="••••••••"
							disabled={loading}
							on:keydown={handleKeydown}
							class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none disabled:opacity-50 disabled:cursor-not-allowed"
							required
						/>
					</div>

					<!-- Error Message -->
					{#if error}
						<div class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
							{error}
						</div>
					{/if}

					<!-- Submit Button -->
					<button
						type="submit"
						disabled={loading}
						class="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
					>
						{#if loading}
							<svg class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
							</svg>
							Iniciando sesión...
						{:else}
							Iniciar sesión
						{/if}
					</button>
				</form>

				<!-- Info -->
				<div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
					<p class="text-sm text-blue-800">
						<strong>Demo:</strong> Usa tus credenciales de Supabase para acceder.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}
