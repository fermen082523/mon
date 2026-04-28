<script>
  export let data = []; // Array de { label, value }
  
  const COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', 
    '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#64748b'
  ];

  $: total = data.reduce((sum, item) => sum + item.value, 0);
  
  $: chartSegments = data.map((item, i) => {
    const percentage = (item.value / total) * 100;
    return {
      ...item,
      percentage,
      color: COLORS[i % COLORS.length]
    };
  });

  $: conicGradient = chartSegments.reduce((acc, segment, i) => {
    const prevPercentage = chartSegments.slice(0, i).reduce((sum, s) => sum + s.percentage, 0);
    const start = prevPercentage;
    const end = prevPercentage + segment.percentage;
    return `${acc}${segment.color} ${start}% ${end}%${i === chartSegments.length - 1 ? '' : ', '}`;
  }, '');
</script>

<div class="flex flex-col lg:flex-row items-center gap-6 md:gap-10 p-5 md:p-8 bg-white rounded-3xl border-2 border-slate-200 shadow-md relative overflow-hidden h-full">
  {#if data.length > 0}
    <!-- Pie Circle -->
    <div class="relative h-40 w-40 md:h-52 md:w-52 rounded-full shadow-inner flex-shrink-0" 
         style="background: conic-gradient({conicGradient});">
      <div class="absolute inset-7 md:inset-10 bg-white rounded-full flex items-center justify-center flex-col shadow-sm">
        <span class="text-2xl md:text-4xl font-black text-slate-900 leading-none">{total}</span>
        <span class="text-[9px] md:text-[10px] font-black uppercase tracking-widest text-slate-400 mt-1">Total</span>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex-1 w-full space-y-4">
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-[10px] md:text-xs font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
          <span class="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
          Productividad Equipo
        </h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
        {#each chartSegments as segment}
          <div class="flex items-center justify-between group py-1 border-b border-slate-50 sm:border-none">
            <div class="flex items-center gap-3">
              <div class="h-2.5 w-2.5 rounded-full shadow-sm shrink-0" style="background-color: {segment.color}"></div>
              <span class="text-xs font-bold text-slate-600 group-hover:text-indigo-600 transition-colors uppercase truncate max-w-[100px] md:max-w-none">{segment.label}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-[9px] font-black text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full">{segment.percentage.toFixed(0)}%</span>
              <span class="text-xs font-black text-slate-900 w-6 text-right">{segment.value}</span>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {:else}
    <div class="w-full py-12 flex flex-col items-center justify-center text-slate-300">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mb-3 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
      </svg>
      <p class="text-xs font-black uppercase tracking-widest">Sin datos para graficar</p>
    </div>
  {/if}
</div>
