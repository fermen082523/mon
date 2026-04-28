<script lang="ts">
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let label: string;
	export let value: number;
	export let estado: string;
	export let color: string = 'blue';
	export let active: boolean = false;

	const displayedValue = tweened(0, {
		duration: 600,
		easing: cubicOut
	});

	$: displayedValue.set(value);

	const themeMap: Record<string, { activeBg: string, inactiveBg: string, activeText: string, inactiveText: string, borderColor: string, shadow: string }> = {
		blue: {
			activeBg: '#4f46e5',
			inactiveBg: '#ffffff',
			activeText: '#ffffff',
			inactiveText: '#4f46e5',
			borderColor: '#cbd5e1',
			shadow: '0 20px 25px -5px rgba(79, 70, 229, 0.4)'
		},
		green: {
			activeBg: '#059669',
			inactiveBg: '#ffffff',
			activeText: '#ffffff',
			inactiveText: '#059669',
			borderColor: '#cbd5e1',
			shadow: '0 20px 25px -5px rgba(5, 150, 105, 0.4)'
		},
		yellow: {
			activeBg: '#d97706',
			inactiveBg: '#ffffff',
			activeText: '#ffffff',
			inactiveText: '#d97706',
			borderColor: '#cbd5e1',
			shadow: '0 20px 25px -5px rgba(217, 119, 6, 0.4)'
		},
		red: {
			activeBg: '#dc2626',
			inactiveBg: '#ffffff',
			activeText: '#ffffff',
			inactiveText: '#dc2626',
			borderColor: '#cbd5e1',
			shadow: '0 20px 25px -5px rgba(220, 38, 38, 0.4)'
		},
		purple: {
			activeBg: '#7c3aed',
			inactiveBg: '#ffffff',
			activeText: '#ffffff',
			inactiveText: '#7c3aed',
			borderColor: '#cbd5e1',
			shadow: '0 20px 25px -5px rgba(124, 58, 237, 0.4)'
		}
	};

	$: theme = themeMap[color] || themeMap.blue;
</script>

<button 
	on:click={() => dispatch('click')}
	class="w-full text-left p-4 md:p-5 rounded-3xl transition-all duration-300 group relative border-2 active:scale-95 flex flex-col justify-between h-full min-h-[100px] md:min-h-[120px] shadow-sm hover:shadow-md"
	style="
		background-color: {active ? theme.activeBg : theme.inactiveBg}; 
		color: {active ? theme.activeText : theme.inactiveText}; 
		border-color: {active ? theme.activeBg : theme.borderColor};
		box-shadow: {active ? theme.shadow : ''};
	"
>
	<div class="space-y-1">
		<p class="text-[9px] md:text-[10px] font-black uppercase tracking-[0.2em] {active ? 'opacity-80' : 'text-slate-400'}">
			{label}
		</p>
		<p class="text-3xl md:text-4xl font-black tracking-tighter leading-none">
			{Math.round($displayedValue)}
		</p>
	</div>
	
	<div class="flex items-center justify-between mt-auto pt-2">
		<span class="text-[8px] font-bold uppercase tracking-widest {active ? 'opacity-70' : 'text-slate-300'}">
			{active ? 'Seleccionado' : 'Filtrar'}
		</span>
		<div class="h-1.5 w-1.5 rounded-full {active ? 'bg-white' : 'bg-slate-200'}"></div>
	</div>
</button>
