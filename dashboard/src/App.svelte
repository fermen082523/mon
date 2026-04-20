<script>
  import { onMount } from 'svelte';
  import { supabase } from './lib/supabase';
  import StatCard from './lib/StatCard.svelte';
  import OrdenesTable from './lib/OrdenesTable.svelte';

  const SESSION_KEY = 'monitor_dashboard_user';
  const PAGE_SIZE = 25;

  let currentUser = null;
  let username = '';
  let password = '';
  let loginError = '';
  let loadingLogin = false;

  let ordenes = [];
  let users = [];
  let stats = { pendiente: 0, solicitada: 0, finalizada: 0, error: 0, anulada: 0 };
  let globalStats = { pendiente: 0, solicitada: 0, finalizada: 0, error: 0, anulada: 0 };
  let colaActiva = [];

  let page = 1;
  let totalItems = 0;
  let totalPages = 1;
  let loadingData = false;
  let loadingUsers = false;
  let loadingSearch = false;

  let filtroEstado = 'TODAS';
  let searchPlateInput = '';
  let activeSearchPlate = '';
  let searchDebounceTimer = null;

  let monitorOwnCount = 0;
  let monitorOthersCount = 0;
  let totalHoy = 0;

  let ingestTag = '';
  let ingestText = '';
  let ingestReport = '';
  let loadingIngest = false;

  let userForm = { username: '', password: '', role: 'monitor', etiqueta: '' };
  let userActionReport = '';
  let resetTarget = '';
  let resetPasswordValue = '';

  let showChangePasswordPanel = false;
  let myCurrentPassword = '';
  let myNewPassword = '';
  let myNewPasswordConfirm = '';
  let myPasswordReport = '';
  let loadingMyPassword = false;

  function normalizeTag(tag) {
    return (tag || '').trim().toLowerCase();
  }

  function roleLabel(role) {
    if (role === 'operador') return 'Operador';
    if (role === 'digitador') return 'Digitador';
    return 'Monitor';
  }

  async function hashPassword(plain) {
    const encoder = new TextEncoder();
    const data = encoder.encode(plain);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  function isMonitor() {
    return currentUser?.role === 'monitor';
  }

  function isDigitador() {
    return currentUser?.role === 'digitador';
  }

  function isOperador() {
    return currentUser?.role === 'operador';
  }

  function totalGlobalPlacas() {
    return (
      (stats.pendiente || 0) +
      (stats.solicitada || 0) +
      (stats.finalizada || 0) +
      (stats.error || 0) +
      (stats.anulada || 0)
    );
  }

  function applyRoleScope(query) {
    if (isMonitor()) {
      const tag = normalizeTag(currentUser?.etiqueta);
      // Inicio del día en GMT-5: medianoche local GMT-5 = 05:00 UTC
      const ahora = new Date();
      const offsetMs = 5 * 60 * 60 * 1000; // UTC-5
      const enGmt5 = new Date(ahora.getTime() - offsetMs);
      // Trucamos al inicio del día en GMT-5
      enGmt5.setUTCHours(0, 0, 0, 0);
      // Convertimos de vuelta a UTC para la query (supabase almacena en UTC)
      const hoyInicioUTC = new Date(enGmt5.getTime() + offsetMs);
      return query
        .eq('etiqueta', tag)
        .gte('created_at', hoyInicioUTC.toISOString());
    }
    return query;
  }

  function applySearchScope(query) {
    if (activeSearchPlate) {
      return query.ilike('placa', `%${activeSearchPlate}%`);
    }
    return query;
  }

  function isPlacaValida(value) {
    const plate = value.trim().toUpperCase();
    return /^[A-Z]{2,3}[0-9]{3,4}[A-Z]?$/.test(plate);
  }

  function parsePlacas(raw) {
    const lines = raw
      .split(/\r?\n/)
      .map((v) => v.trim().toUpperCase())
      .filter(Boolean);

    const unique = Array.from(new Set(lines));
    const valid = [];
    const invalid = [];

    for (const plate of unique) {
      if (isPlacaValida(plate)) valid.push(plate);
      else invalid.push(plate);
    }
    return { valid, invalid };
  }

  async function loadOrdenes(targetPage = page) {
    loadingData = true;

    let query = supabase
      .from('rtv_ordenes')
      .select('local_id, placa, numero_orden, estado, etiqueta, updated_at', { count: 'exact' });

    query = applyRoleScope(query);
    query = applySearchScope(query);
    if (filtroEstado !== 'TODAS') {
      query = query.eq('estado', filtroEstado);
    }

    const from = (targetPage - 1) * PAGE_SIZE;
    const to = from + PAGE_SIZE - 1;

    const { data, error, count } = await query
      .order('updated_at', { ascending: false })
      .range(from, to);

    if (!error) {
      ordenes = data ?? [];
      totalItems = count ?? 0;
      totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
      page = Math.min(Math.max(1, targetPage), totalPages);
    }

    loadingData = false;
  }

  async function countByEstado(estado) {
    let query = supabase
      .from('rtv_ordenes')
      .select('local_id', { count: 'exact', head: true })
      .eq('estado', estado);

    query = applyRoleScope(query);

    const { count, error } = await query;
    if (error) return 0;
    return count ?? 0;
  }

  async function loadStats() {
    const [pendiente, solicitada, finalizada, error, anulada] = await Promise.all([
      countByEstado('PENDIENTE_SOLICITUD'),
      countByEstado('SOLICITADA'),
      countByEstado('FINALIZADA'),
      countByEstado('ERROR'),
      countByEstado('ANULADA'),
    ]);

    stats = { pendiente, solicitada, finalizada, error, anulada };
  }

  async function loadGlobalStats() {
    if (!isDigitador()) return;
    const estados = ['PENDIENTE_SOLICITUD', 'SOLICITADA', 'FINALIZADA', 'ERROR', 'ANULADA'];
    const counts = await Promise.all(estados.map(async (estado) => {
      const { count } = await supabase
        .from('rtv_ordenes')
        .select('local_id', { count: 'exact', head: true })
        .eq('estado', estado);
      return count ?? 0;
    }));
    globalStats = {
      pendiente: counts[0],
      solicitada: counts[1],
      finalizada: counts[2],
      error: counts[3],
      anulada: counts[4],
    };
  }

  async function loadColaActiva() {
    let query = supabase
      .from('rtv_ordenes')
      .select('placa, etiqueta, created_at')
      .eq('estado', 'PENDIENTE_SOLICITUD');

    query = applyRoleScope(query);

    const { data } = await query.order('created_at', { ascending: true }).limit(20);
    colaActiva = data ?? [];
  }

  async function loadMonitorCounters() {
    if (!isMonitor()) {
      monitorOwnCount = 0;
      monitorOthersCount = 0;
      return;
    }

    const myTag = normalizeTag(currentUser?.etiqueta);

    const own = await supabase
      .from('rtv_ordenes')
      .select('local_id', { count: 'exact', head: true })
      .eq('etiqueta', myTag);

    const others = await supabase
      .from('rtv_ordenes')
      .select('local_id', { count: 'exact', head: true })
      .not('etiqueta', 'is', null)
      .neq('etiqueta', myTag);

    monitorOwnCount = own.count ?? 0;
    monitorOthersCount = others.count ?? 0;
  }

  async function loadTotalHoy() {
    const ahora = new Date();
    const offsetMs = 5 * 60 * 60 * 1000; // UTC-5 (Colombia)
    const enGmt5 = new Date(ahora.getTime() - offsetMs);
    enGmt5.setUTCHours(0, 0, 0, 0);
    const hoyInicioUTC = new Date(enGmt5.getTime() + offsetMs);

    const { count } = await supabase
      .from('rtv_ordenes')
      .select('local_id', { count: 'exact', head: true })
      .gte('created_at', hoyInicioUTC.toISOString());

    totalHoy = count ?? 0;
  }

  async function refreshDashboard(targetPage = page) {
    await Promise.all([
      loadOrdenes(targetPage),
      loadStats(),
      loadGlobalStats(),
      loadColaActiva(),
      loadMonitorCounters(),
      loadTotalHoy(),
    ]);
  }

  async function loadUsers() {
    if (!isOperador()) return;
    loadingUsers = true;

    const { data, error } = await supabase
      .from('app_users')
      .select('username, role, etiqueta, active')
      .order('username', { ascending: true });

    if (!error) {
      users = data ?? [];
    }

    loadingUsers = false;
  }

  async function doLogin() {
    loadingLogin = true;
    loginError = '';

    const inputUsername = username.trim();
    const inputPassword = password;

    if (!inputUsername || !inputPassword) {
      loginError = 'Ingresa usuario y clave.';
      loadingLogin = false;
      return;
    }

    const hashedInputPassword = await hashPassword(inputPassword);

    const { data, error } = await supabase
      .from('app_users')
      .select('username, role, etiqueta, active')
      .ilike('username', inputUsername)
      .eq('password', hashedInputPassword)
      .eq('active', true)
      .maybeSingle();

    if (error) {
      loginError = `Error de acceso: ${error.message}`;
      loadingLogin = false;
      return;
    }

    let loginData = data;

    // Compatibilidad temporal
    if (!loginData) {
      const legacy = await supabase
        .from('app_users')
        .select('username, role, etiqueta, active')
        .ilike('username', inputUsername)
        .eq('password', inputPassword)
        .eq('active', true)
        .maybeSingle();

      if (legacy.error) {
        loginError = `Error de acceso: ${legacy.error.message}`;
        loadingLogin = false;
        return;
      }

      loginData = legacy.data;
    }

    if (!loginData) {
      loginError = 'Usuario o clave incorrectos.';
      loadingLogin = false;
      return;
    }

    currentUser = {
      username: loginData.username,
      role: loginData.role,
      etiqueta: loginData.etiqueta,
    };

    localStorage.setItem(SESSION_KEY, JSON.stringify(currentUser));
    username = '';
    password = '';

    await refreshDashboard(1);
    await loadUsers();

    loadingLogin = false;
  }

  function doLogout() {
    currentUser = null;
    ordenes = [];
    users = [];
    localStorage.removeItem(SESSION_KEY);
  }


  async function searchByPlate(val) {
    loadingSearch = true;
    activeSearchPlate = val.trim().toUpperCase();
    await refreshDashboard(1);
    loadingSearch = false;
  }

  async function handleSearchInput() {
    const val = searchPlateInput.trim();
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    if (val.length >= 2) {
      searchDebounceTimer = setTimeout(async () => {
        await searchByPlate(searchPlateInput);
      }, 350);
    } else if (val.length === 0) {
      activeSearchPlate = '';
      await refreshDashboard(1);
    }
  }

  async function clearSearch() {
    searchPlateInput = '';
    activeSearchPlate = '';
    await refreshDashboard(1);
  }

  async function goToPage(nextPage) {
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) return;
    await loadOrdenes(nextPage);
  }

  async function ingestPlacas() {
    ingestReport = '';

    const tag = normalizeTag(ingestTag);
    if (!/^[a-z]{2}$/.test(tag)) {
      ingestReport = 'La etiqueta debe tener exactamente 2 letras (ej: ca).';
      return;
    }

    const { valid, invalid } = parsePlacas(ingestText);
    if (!valid.length) {
      ingestReport = `No hay placas validas para cargar. Invalidas: ${invalid.length}.`;
      return;
    }

    loadingIngest = true;

    const now = new Date().toISOString();
    const base = Date.now();
    const payload = valid.map((placa, idx) => ({
      local_id: -(base + idx),
      placa,
      numero_orden: null,
      estado: 'PENDIENTE_SOLICITUD',
      intentos: 0,
      origen: 'WEB_PANEL',
      etiqueta: tag,
      created_at: now,
      updated_at: now,
      finalizar_after: null,
    }));

    const { error } = await supabase.from('rtv_ordenes').upsert(payload, { onConflict: 'local_id' });

    loadingIngest = false;

    if (error) {
      ingestReport = `Error al registrar placas: ${error.message}`;
      return;
    }

    ingestText = '';
    ingestReport = `Cargadas ${valid.length} placas. Invalidas omitidas: ${invalid.length}.`;
    await refreshDashboard(page);
  }

  async function createUser() {
    userActionReport = '';

    const u = userForm.username.trim().toLowerCase();
    const p = userForm.password;
    const r = userForm.role;
    const tag = normalizeTag(userForm.etiqueta);

    if (!u || !p) {
      userActionReport = 'Usuario y clave son obligatorios.';
      return;
    }

    if (!['monitor', 'digitador', 'operador'].includes(r)) {
      userActionReport = 'Rol invalido.';
      return;
    }

    if (r === 'monitor' && !/^[a-z]{2}$/.test(tag)) {
      userActionReport = 'El monitor requiere etiqueta de 2 letras.';
      return;
    }

    const payload = {
      username: u,
      password: await hashPassword(p),
      role: r,
      etiqueta: r === 'monitor' ? tag : null,
      active: true,
    };

    const { error } = await supabase.from('app_users').upsert(payload, { onConflict: 'username' });

    if (error) {
      userActionReport = `No se pudo crear usuario: ${error.message}`;
      return;
    }

    userActionReport = `Usuario ${u} creado/actualizado.`;
    userForm = { username: '', password: '', role: 'monitor', etiqueta: '' };
    await loadUsers();
  }

  async function resetPassword() {
    userActionReport = '';

    const u = resetTarget.trim().toLowerCase();
    const p = resetPasswordValue;

    if (!u || !p) {
      userActionReport = 'Usuario y nueva clave son obligatorios.';
      return;
    }

    const { error } = await supabase
      .from('app_users')
      .update({ password: await hashPassword(p) })
      .eq('username', u);

    if (error) {
      userActionReport = `No se pudo cambiar clave: ${error.message}`;
      return;
    }

    userActionReport = `Clave actualizada para ${u}.`;
    resetTarget = '';
    resetPasswordValue = '';
  }

  async function changeMyPassword() {
    myPasswordReport = '';
    const usernameValue = currentUser?.username?.trim();

    if (!usernameValue) {
      myPasswordReport = 'No hay sesion activa.';
      return;
    }

    if (!myCurrentPassword || !myNewPassword || !myNewPasswordConfirm) {
      myPasswordReport = 'Completa todos los campos para cambiar tu clave.';
      return;
    }

    if (myNewPassword !== myNewPasswordConfirm) {
      myPasswordReport = 'La nueva clave y su confirmacion no coinciden.';
      return;
    }

    if (myNewPassword.length < 6) {
      myPasswordReport = 'La nueva clave debe tener al menos 6 caracteres.';
      return;
    }

    loadingMyPassword = true;

    const hashedCurrentPassword = await hashPassword(myCurrentPassword);

    const { data: userData, error: userError } = await supabase
      .from('app_users')
      .select('username')
      .ilike('username', usernameValue)
      .eq('password', hashedCurrentPassword)
      .eq('active', true)
      .maybeSingle();

    if (userError) {
      myPasswordReport = `No se pudo validar la clave actual: ${userError.message}`;
      loadingMyPassword = false;
      return;
    }

    let currentUserData = userData;

    if (!currentUserData) {
      const legacy = await supabase
        .from('app_users')
        .select('username')
        .ilike('username', usernameValue)
        .eq('password', myCurrentPassword)
        .eq('active', true)
        .maybeSingle();

      if (legacy.error) {
        myPasswordReport = `No se pudo validar la clave actual: ${legacy.error.message}`;
        loadingMyPassword = false;
        return;
      }

      currentUserData = legacy.data;
    }

    if (!currentUserData) {
      myPasswordReport = 'La clave actual es incorrecta.';
      loadingMyPassword = false;
      return;
    }

    const { error: updateError } = await supabase
      .from('app_users')
      .update({ password: await hashPassword(myNewPassword) })
      .ilike('username', usernameValue);

    loadingMyPassword = false;

    if (updateError) {
      myPasswordReport = `No se pudo cambiar tu clave: ${updateError.message}`;
      return;
    }

    myCurrentPassword = '';
    myNewPassword = '';
    myNewPasswordConfirm = '';
    myPasswordReport = 'Tu clave fue actualizada correctamente.';
  }

  function toggleChangePasswordPanel() {
    showChangePasswordPanel = !showChangePasswordPanel;
    if (!showChangePasswordPanel) {
      myCurrentPassword = '';
      myNewPassword = '';
      myNewPasswordConfirm = '';
      myPasswordReport = '';
    }
  }

  onMount(async () => {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) {
      try {
        currentUser = JSON.parse(saved);
      } catch {
        currentUser = null;
      }
    }

    if (currentUser) {
      await refreshDashboard(1);
      await loadUsers();
    }

    const realtime = supabase
      .channel('monitor-dashboard-live')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'rtv_ordenes' }, async () => {
        if (currentUser) await refreshDashboard(page);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(realtime);
    };
  });
</script>

{#if !currentUser}
  <main class="min-h-[100dvh] bg-[#f8fafc] flex flex-col items-center md:justify-center p-4 pt-16 md:pt-4 pb-12 relative overflow-x-hidden overflow-y-auto">
    <!-- Decorative background (No blur for Safari performance) -->
    <div class="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-indigo-500/5 rounded-full pointer-events-none"></div>
    <div class="absolute bottom-0 right-0 w-[40%] h-[40%] bg-rose-500/5 rounded-full pointer-events-none"></div>

    <section class="w-full max-w-md bg-white/80 backdrop-blur-xl rounded-[2rem] shadow-2xl p-8 border border-white relative z-10">
      <div class="flex justify-center mb-6">
        <div class="h-14 w-14 bg-gradient-to-br from-indigo-600 to-violet-700 rounded-2xl flex items-center justify-center text-white text-2xl font-black shadow-lg shadow-indigo-200">
          M
        </div>
      </div>
      <h1 class="text-3xl font-black text-center text-slate-900 tracking-tight">RTV Live</h1>
      <p class="text-sm font-bold text-center text-slate-500 mt-2 uppercase tracking-widest">Acceso Seguro</p>

      <form class="mt-8 space-y-5" on:submit|preventDefault={doLogin}>
        <div>
          <label class="block text-xs font-black text-slate-600 uppercase tracking-widest mb-2" for="username">Usuario</label>
          <input id="username" type="text" bind:value={username} required class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-3 outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold transition-all" placeholder="Ingresa tu usuario" />
        </div>
        <div>
          <label class="block text-xs font-black text-slate-600 uppercase tracking-widest mb-2" for="password">Clave</label>
          <input id="password" type="password" bind:value={password} required class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-3 outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold transition-all" placeholder="••••••••" />
        </div>
        {#if loginError}
          <p class="text-xs font-bold text-rose-600 bg-rose-50 border-2 border-rose-100 rounded-xl px-4 py-3">{loginError}</p>
        {/if}
        <button type="submit" disabled={loadingLogin} class="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-4 font-black tracking-widest uppercase shadow-lg shadow-indigo-200 transition-all active:scale-95 disabled:opacity-60 mt-4">
          {loadingLogin ? 'Verificando...' : 'Ingresar'}
        </button>
      </form>
    </section>
  </main>
{:else}
  <main class="relative min-h-[100dvh] bg-[#f8fafc] pb-20 md:pb-10">
    <!-- Background Color Accents (No blur for Safari performance) -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <div class="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-indigo-500/5 rounded-full"></div>
      <div class="absolute bottom-0 right-0 w-[40%] h-[40%] bg-rose-500/5 rounded-full"></div>
    </div>

    <!-- Header App Style -->
    <header class="sticky top-0 z-[60] bg-white/80 backdrop-blur-xl border-b border-slate-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 md:h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="h-8 w-8 bg-gradient-to-br from-indigo-600 to-violet-700 rounded-xl flex items-center justify-center text-white font-black shadow-md shadow-indigo-200">
            M
          </div>
          <div>
            <h1 class="text-sm md:text-base font-black text-slate-900 tracking-tight leading-none">RTV Live</h1>
            <p class="text-[9px] md:text-[10px] font-black text-slate-400 uppercase tracking-widest mt-0.5">{roleLabel(currentUser.role)}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button on:click={toggleChangePasswordPanel} class="p-2 text-slate-400 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 rounded-xl transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </button>
          <button on:click={doLogout} class="flex items-center gap-2 px-3 py-2 bg-rose-50 text-rose-600 rounded-xl font-bold text-xs hover:bg-rose-100 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M17 16l4-4m0 0l-4-4m4 4H7" /></svg>
            <span class="hidden md:block">Salir</span>
          </button>
        </div>
      </div>
    </header>

    <section class="relative z-10 max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      
      <!-- Panel de contraseña -->
      {#if showChangePasswordPanel}
        <div class="bg-white rounded-[2rem] shadow-sm border border-slate-100 p-6 space-y-4">
          <h3 class="font-black text-slate-900 tracking-tight text-lg">Cambiar Clave</h3>
          <div class="grid md:grid-cols-3 gap-4">
            <div>
              <label for="my-current-password" class="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Clave actual</label>
              <input id="my-current-password" type="password" bind:value={myCurrentPassword} class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-2 font-bold" />
            </div>
            <div>
              <label for="my-new-password" class="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Nueva clave</label>
              <input id="my-new-password" type="password" bind:value={myNewPassword} class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-2 font-bold" />
            </div>
            <div>
              <label for="my-new-password-confirm" class="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Confirmar clave</label>
              <input id="my-new-password-confirm" type="password" bind:value={myNewPasswordConfirm} class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-2 font-bold" />
            </div>
          </div>
          <div class="flex items-center gap-3 pt-2">
            <button on:click={changeMyPassword} disabled={loadingMyPassword} class="px-6 py-3 rounded-xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest shadow-md shadow-indigo-200 disabled:opacity-60">
              {loadingMyPassword ? 'Actualizando...' : 'Guardar'}
            </button>
            {#if myPasswordReport}
              <p class="text-xs font-bold text-indigo-600">{myPasswordReport}</p>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Operador Ingestion Panel -->
      {#if isOperador()}
        <div class="bg-white rounded-[2rem] shadow-sm border border-slate-100 p-6 space-y-4">
          <div class="flex items-center gap-3 mb-2">
            <div class="h-10 w-10 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            </div>
            <div>
              <h3 class="font-black text-slate-900 tracking-tight text-lg">Carga de Placas</h3>
              <p class="text-[10px] font-black uppercase tracking-widest text-slate-400">Ingreso masivo</p>
            </div>
          </div>
          
          <div class="grid md:grid-cols-4 gap-4">
            <div class="md:col-span-1">
              <label for="ingest-tag" class="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Etiqueta (2 letras)</label>
              <input id="ingest-tag" type="text" maxlength="2" bind:value={ingestTag} placeholder="ca" class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-3 font-black text-indigo-600 uppercase focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none transition-all text-center text-xl" />
            </div>
            <div class="md:col-span-3">
              <label for="ingest-placas" class="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Listado de Placas (Una por línea)</label>
              <textarea id="ingest-placas" rows="4" bind:value={ingestText} placeholder="ABC1234&#10;XYZ9876" class="w-full bg-slate-50 border-2 border-slate-100 rounded-xl px-4 py-3 font-bold focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none transition-all"></textarea>
            </div>
          </div>
          <div class="flex flex-col sm:flex-row sm:items-center gap-4 pt-2">
            <button on:click={ingestPlacas} disabled={loadingIngest} class="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest shadow-lg shadow-indigo-200 hover:bg-indigo-700 active:scale-95 transition-all disabled:opacity-60">
              {loadingIngest ? 'Registrando...' : 'Registrar Placas'}
            </button>
            {#if ingestReport}
              <p class="text-xs font-bold text-slate-600 bg-slate-50 py-2 px-4 rounded-lg border border-slate-200">{ingestReport}</p>
            {/if}
          </div>
        </div>

        <!-- ...resto de menus de operador... -->
      {/if}

      <!-- Total del día - visible para todos los roles -->
      <div class="flex items-center gap-5 bg-white rounded-[2rem] border border-slate-100 shadow-sm px-6 py-5 overflow-hidden relative">
        <div class="absolute right-0 top-0 h-full w-32 bg-gradient-to-l from-emerald-50 to-transparent pointer-events-none"></div>
        <div class="h-12 w-12 shrink-0 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-200/60">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <p class="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Órdenes Hoy</p>
          <p class="text-4xl md:text-5xl font-black text-slate-900 tracking-tighter leading-none">{totalHoy}</p>
        </div>
      </div>

      <!-- Main Statistics Row -->
      {#if !isDigitador()}
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="En Cola" value={stats.pendiente} estado="pendiente" color="blue" />
          <StatCard label="Solicitadas" value={stats.solicitada} estado="solicitada" color="yellow" />
          <StatCard label="Finalizadas" value={stats.finalizada} estado="finalizada" color="green" />
          <StatCard label="Errores" value={stats.error} estado="error" color="red" />
          <StatCard label="Anuladas" value={stats.anulada} estado="anulada" color="purple" />
        </div>
      {/if}

      <!-- App-Like Search and Filters (Sticky) -->
      <div class="sticky top-[56px] md:top-[64px] z-50 py-3 -mx-4 px-4 md:mx-0 md:px-0 bg-[#f8fafc]/90 backdrop-blur-xl">
        <div class="flex flex-col gap-4">
          <div class="flex gap-2">
            <div class="relative flex-1 group">
              <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              </div>
              <input type="text" bind:value={searchPlateInput} on:input={handleSearchInput} placeholder="Buscar placa..." class="block w-full pl-11 pr-4 py-3.5 bg-white border-2 border-slate-100 rounded-[1.5rem] text-sm font-black placeholder:text-slate-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all shadow-sm" />
              {#if searchPlateInput}
                <button on:click={clearSearch} class="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-300 hover:text-slate-600">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>
                </button>
              {/if}
            </div>
            <button on:click={() => refreshDashboard(page)} class="h-[52px] w-[52px] shrink-0 bg-white border-2 border-slate-100 rounded-[1.5rem] flex items-center justify-center text-indigo-600 shadow-sm active:scale-90 transition-all">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
          </div>

          <!-- Colorized Filter Tabs -->
          <div class="flex overflow-x-auto no-scrollbar gap-2 pb-1">
            {#each [
              { id: 'TODAS', label: 'Todos', color: '#64748b' },
              { id: 'PENDIENTE_SOLICITUD', label: 'En Cola', color: '#4f46e5' },
              { id: 'SOLICITADA', label: 'Solicitadas', color: '#f59e0b' },
              { id: 'FINALIZADA', label: 'Finalizadas', color: '#10b981' },
              { id: 'ERROR', label: 'Errores', color: '#ef4444' },
              { id: 'ANULADA', label: 'Anuladas', color: '#64748b' }
            ] as f}
              <button
                on:click={async () => { filtroEstado = f.id; await refreshDashboard(1); }}
                class="whitespace-nowrap px-5 py-2.5 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all border-2 active:scale-90"
                style="
                  background-color: {filtroEstado === f.id ? f.color : 'white'};
                  color: {filtroEstado === f.id ? 'white' : f.color};
                  border-color: {f.color};
                  box-shadow: {filtroEstado === f.id ? `0 10px 20px -5px ${f.color}66` : 'none'};
                  opacity: {filtroEstado === f.id ? '1' : '0.6'};
                "
              >
                {f.label}
              </button>
            {/each}
          </div>
        </div>
      </div>

      <!-- Main List View -->
      <div class="relative min-h-[300px]">
        {#if loadingData}
          <div class="absolute inset-0 flex items-center justify-center z-10">
            <div class="flex flex-col items-center gap-4 bg-white/80 p-6 rounded-3xl backdrop-blur-sm">
              <div class="h-10 w-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              <p class="text-[10px] font-black text-indigo-600 uppercase tracking-widest">Sincronizando</p>
            </div>
          </div>
        {/if}

        <div class={loadingData ? 'opacity-30 pointer-events-none transition-opacity duration-300' : 'transition-opacity duration-300'}>
          <OrdenesTable ordenes={ordenes} isMonitor={isMonitor()} isDigitador={isDigitador()} />
        </div>
      </div>

      <!-- Native-style Pagination -->
      {#if totalPages > 1}
        <div class="flex items-center justify-between bg-white px-4 py-3 rounded-[2rem] border border-slate-100 shadow-sm mt-4">
          <button on:click={() => goToPage(page - 1)} disabled={page <= 1} class="p-3 bg-slate-50 text-slate-700 rounded-xl disabled:opacity-30 active:scale-90 transition-transform">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>
          </button>
          <div class="flex flex-col items-center">
            <span class="text-xs font-black text-slate-900 tracking-widest">PÁGINA {page}</span>
            <span class="text-[9px] font-bold text-slate-400 uppercase tracking-widest">DE {totalPages}</span>
          </div>
          <button on:click={() => goToPage(page + 1)} disabled={page >= totalPages} class="p-3 bg-indigo-50 text-indigo-600 rounded-xl disabled:opacity-30 active:scale-90 transition-transform">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" /></svg>
          </button>
        </div>
      {/if}
    </section>
  </main>
{/if}

<style>
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
