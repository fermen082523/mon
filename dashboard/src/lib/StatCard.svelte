<script lang="ts">
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';

	export let label: string;
	export let value: number;
	export let estado: string;
	export let color: string = 'blue';

	const displayedValue = tweened(0, {
		duration: 600,
		easing: cubicOut
	});

	$: displayedValue.set(value);

	// Colores ultra-vibrantes con degradados
	const themeMap: Record<string, { bg: string, text: string, iconBg: string, shadow: string }> = {
		blue: {
			bg: 'linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)',
			text: '#ffffff',
			iconBg: 'rgba(255, 255, 255, 0.2)',
			shadow: '0 10px 25px -5px rgba(59, 130, 246, 0.5)'
		},
		green: {
			bg: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
			text: '#ffffff',
			iconBg: 'rgba(255, 255, 255, 0.2)',
			shadow: '0 10px 25px -5px rgba(16, 185, 129, 0.5)'
		},
		yellow: {
			bg: 'linear-gradient(135deg, #d97706 0%, #f59e0b 100%)',
			text: '#ffffff',
			iconBg: 'rgba(255, 255, 255, 0.2)',
			shadow: '0 10px 25px -5px rgba(245, 158, 11, 0.5)'
		},
		red: {
			bg: 'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)',
			text: '#ffffff',
			iconBg: 'rgba(255, 255, 255, 0.2)',
			shadow: '0 10px 25px -5px rgba(239, 68, 68, 0.5)'
		},
		purple: {
			bg: 'linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%)',
			text: '#ffffff',
			iconBg: 'rgba(255, 255, 255, 0.2)',
			shadow: '0 10px 25px -5px rgba(139, 92, 246, 0.5)'
		}
	};

	const theme = themeMap[color] || themeMap.blue;

	const iconMap: Record<string, string> = {
		pendiente: '⏳',
		solicitada: '📋',
		finalizada: '✅',
		error: '❌',
		anulada: '🚫',
	};
</script>

<div 
	class="p-4 md:p-6 rounded-[2rem] transition-all duration-500 group overflow-hidden relative border border-white/10 active:scale-95"
	style="background: {theme.bg}; color: {theme.text}; box-shadow: {theme.shadow};"
>
	<!-- Shine effect -->
	<div class="absolute -right-4 -top-4 h-32 w-32 bg-white/20 blur-3xl rounded-full transition-transform group-hover:scale-150 duration-700"></div>
	
	<div class="flex items-center justify-between relative z-10">
		<div class="space-y-1">
			<p class="text-[9px] md:text-xs font-black uppercase tracking-[0.2em] opacity-90">{label}</p>
			<div class="flex items-baseline">
				<p class="text-3xl md:text-5xl font-black tracking-tighter leading-none">
					{Math.round($displayedValue)}
				</p>
			</div>
		</div>
		<div 
			class="h-10 w-10 md:h-16 md:w-16 rounded-2xl md:rounded-3xl backdrop-blur-md flex items-center justify-center text-xl md:text-4xl shadow-inner border border-white/30 transition-all group-hover:scale-110 group-hover:rotate-6 duration-300"
			style="background: {theme.iconBg};"
		>
			{iconMap[estado] || '📊'}
		</div>
	</div>
</div>
