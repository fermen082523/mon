<script lang="ts">
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';

	export let label: string;
	export let value: number;
	export let estado: string;
	export let color: string = 'blue';

	const displayedValue = tweened(0, {
		duration: 400,
		easing: cubicOut
	});

	$: displayedValue.set(value);

	const colorMap: Record<string, string> = {
		blue: 'bg-blue-50/50 text-blue-700 border-blue-100 ring-blue-500/5 hover:bg-blue-50',
		green: 'bg-emerald-50/50 text-emerald-700 border-emerald-100 ring-emerald-500/5 hover:bg-emerald-50',
		yellow: 'bg-amber-50/50 text-amber-700 border-amber-100 ring-amber-500/5 hover:bg-amber-50',
		red: 'bg-rose-50/50 text-rose-700 border-rose-100 ring-rose-500/5 hover:bg-rose-50',
		purple: 'bg-indigo-50/50 text-indigo-700 border-indigo-100 ring-indigo-500/5 hover:bg-indigo-50',
	};

	const iconMap: Record<string, string> = {
		pendiente: '⏳',
		solicitada: '📋',
		finalizada: '✅',
		error: '❌',
		anulada: '🚫',
	};
</script>

<div class={`p-4 md:p-6 border rounded-3xl ring-1 transition-all duration-500 group overflow-hidden relative ${colorMap[color]}`}>
	<!-- Decorative Background Circle -->
	<div class="absolute -right-2 -bottom-2 h-16 w-16 bg-current opacity-[0.03] rounded-full scale-150 transition-transform group-hover:scale-[2] duration-700"></div>

	<div class="flex items-center justify-between relative z-10">
		<div class="space-y-1">
			<p class="text-[10px] md:text-xs font-bold uppercase tracking-[0.15em] opacity-60">{label}</p>
			<div class="flex items-baseline gap-1">
				<p class="text-2xl md:text-4xl font-black tracking-tighter leading-none">
					{Math.round($displayedValue)}
				</p>
				{#if value > 0}
					<span class="h-1.5 w-1.5 rounded-full bg-current animate-pulse"></span>
				{/if}
			</div>
		</div>
		<div class="h-12 w-12 md:h-14 md:w-14 rounded-2xl bg-white shadow-sm border border-white/60 flex items-center justify-center text-2xl md:text-3xl transition-transform group-hover:scale-110 group-hover:rotate-3 duration-300">
			{iconMap[estado] || '📊'}
		</div>
	</div>
</div>
