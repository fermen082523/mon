<script>
  import { onMount } from 'svelte';
  import { supabase } from './lib/supabase';

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

  let monitorOwnCount = 0;
  let monitorOthersCount = 0;

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

  $: ordenesFiltradas = filtroEstado === 'TODAS'
    ? ordenes
    : ordenes.filter((o) => o.estado === filtroEstado);

  function normalizeTag(tag) {
    return (tag || '').trim().toLowerCase();
  }

  function roleLabel(role) {
    if (role === 'operador') return 'Operador';
    if (role === 'digitador') return 'Digitador';
    return 'Monitor';
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
      return query.eq('etiqueta', tag);
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

  async function refreshDashboard(targetPage = page) {
    await Promise.all([
      loadOrdenes(targetPage),
      loadStats(),
      loadColaActiva(),
      loadMonitorCounters(),
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

    const { data, error } = await supabase
      .from('app_users')
      .select('username, role, etiqueta, active')
      .ilike('username', inputUsername)
      .eq('password', inputPassword)
      .eq('active', true)
      .maybeSingle();

    if (error) {
      loginError = `Error de acceso: ${error.message}`;
      loadingLogin = false;
      return;
    }

    if (!data) {
      loginError = 'Usuario o clave incorrectos.';
      loadingLogin = false;
      return;
    }

    currentUser = {
      username: data.username,
      role: data.role,
      etiqueta: data.etiqueta,
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

  async function searchByPlate() {
    loadingSearch = true;
    activeSearchPlate = searchPlateInput.trim().toUpperCase();
    await refreshDashboard(1);
    loadingSearch = false;
  }

  async function handleSearchInput() {
    const val = searchPlateInput.trim();
    if (val.length >= 2) {
      await searchByPlate();
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
      password: p,
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
      .update({ password: p })
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

    const { data: userData, error: userError } = await supabase
      .from('app_users')
      .select('username')
      .ilike('username', usernameValue)
      .eq('password', myCurrentPassword)
      .eq('active', true)
      .maybeSingle();

    if (userError) {
      myPasswordReport = `No se pudo validar la clave actual: ${userError.message}`;
      loadingMyPassword = false;
      return;
    }

    if (!userData) {
      myPasswordReport = 'La clave actual es incorrecta.';
      loadingMyPassword = false;
      return;
    }

    const { error: updateError } = await supabase
      .from('app_users')
      .update({ password: myNewPassword })
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

  function fmt(dt) {
    const parsed = new Date(dt);
    if (Number.isNaN(parsed.getTime())) return dt;
    return parsed.toLocaleString('es-EC', {
      year: '2-digit',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
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
  <main class="min-h-screen bg-slate-100 grid place-items-center p-4">
    <section class="w-full max-w-md bg-white rounded-2xl shadow-xl p-6 border border-slate-200">
      <h1 class="text-2xl font-bold text-slate-900">MONITOR Dashboard</h1>
      <p class="text-sm text-slate-600 mt-1">Acceso con nombre de usuario.</p>

      <form class="mt-6 space-y-4" on:submit|preventDefault={doLogin}>
        <div>
          <label class="block text-sm text-slate-700 mb-1" for="username">Usuario</label>
          <input id="username" type="text" bind:value={username} required class="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-cyan-500" />
        </div>
        <div>
          <label class="block text-sm text-slate-700 mb-1" for="password">Clave</label>
          <input id="password" type="password" bind:value={password} required class="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-cyan-500" />
        </div>
        {#if loginError}
          <p class="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{loginError}</p>
        {/if}
        <button type="submit" disabled={loadingLogin} class="w-full bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg px-4 py-2 font-semibold disabled:opacity-60">
          {loadingLogin ? 'Ingresando...' : 'Ingresar'}
        </button>
      </form>
    </section>
  </main>
{:else}
  <main class="min-h-screen bg-slate-100">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-20">
      <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div>
          <h2 class="font-bold text-slate-900">Dashboard MONITOR</h2>
          <p class="text-xs text-slate-500">
            Usuario: {currentUser.username} | Rol: {roleLabel(currentUser.role)}
            {#if currentUser.etiqueta} | Etiqueta: {currentUser.etiqueta.toUpperCase()}{/if}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button on:click={toggleChangePasswordPanel} class="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-sm">
            {showChangePasswordPanel ? 'Ocultar cambio de clave' : 'Cambiar mi clave'}
          </button>
          <button on:click={doLogout} class="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-sm">Salir</button>
        </div>
      </div>
    </header>

    <section class="max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {#if showChangePasswordPanel}
        <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <h3 class="font-semibold text-slate-900">Cambiar mi clave</h3>
          <div class="grid md:grid-cols-3 gap-3">
            <div>
              <label for="my-current-password" class="block text-xs text-slate-600 mb-1">Clave actual</label>
              <input id="my-current-password" type="password" bind:value={myCurrentPassword} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
            </div>
            <div>
              <label for="my-new-password" class="block text-xs text-slate-600 mb-1">Nueva clave</label>
              <input id="my-new-password" type="password" bind:value={myNewPassword} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
            </div>
            <div>
              <label for="my-new-password-confirm" class="block text-xs text-slate-600 mb-1">Confirmar nueva clave</label>
              <input id="my-new-password-confirm" type="password" bind:value={myNewPasswordConfirm} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
            </div>
          </div>
          <div class="flex items-center gap-3">
            <button on:click={changeMyPassword} disabled={loadingMyPassword} class="px-4 py-2 rounded-lg bg-cyan-700 text-white text-sm disabled:opacity-60">
              {loadingMyPassword ? 'Actualizando...' : 'Actualizar mi clave'}
            </button>
            {#if myPasswordReport}
              <p class="text-sm text-slate-700">{myPasswordReport}</p>
            {/if}
          </div>
        </div>
      {/if}

      {#if isMonitor()}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <article class="bg-white rounded-xl p-4 border border-slate-200">
            <p class="text-xs text-slate-500">Tus placas enviadas</p>
            <p class="text-2xl font-bold">{monitorOwnCount}</p>
          </article>
          <article class="bg-white rounded-xl p-4 border border-slate-200">
            <p class="text-xs text-slate-500">Placas de otros monitores</p>
            <p class="text-2xl font-bold">{monitorOthersCount}</p>
          </article>
        </div>
      {/if}

      {#if isDigitador()}
        <div class="bg-white rounded-xl border border-slate-200 p-4">
          <h3 class="font-semibold text-slate-900">Vista digitador</h3>
          <p class="text-sm text-slate-600 mt-1">Monitoreo global: puedes ver todas las placas registradas.</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
            <article class="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p class="text-xs text-slate-500">Total placas</p>
              <p class="text-2xl font-bold">{totalGlobalPlacas()}</p>
            </article>
            <article class="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p class="text-xs text-slate-500">En proceso</p>
              <p class="text-2xl font-bold">{stats.pendiente + stats.solicitada}</p>
            </article>
            <article class="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p class="text-xs text-slate-500">Con incidencias</p>
              <p class="text-2xl font-bold">{stats.error}</p>
            </article>
          </div>
        </div>
      {/if}

      {#if isOperador()}
        <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <h3 class="font-semibold text-slate-900">Registro de matriculas</h3>
          <p class="text-sm text-slate-600">Carga placas para enviar al flujo de registro.</p>
          <div class="grid md:grid-cols-4 gap-3">
            <div class="md:col-span-1">
              <label for="ingest-tag" class="block text-sm text-slate-700 mb-1">Etiqueta</label>
              <input id="ingest-tag" type="text" maxlength="2" bind:value={ingestTag} placeholder="ca" class="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-cyan-500" />
            </div>
            <div class="md:col-span-3">
              <label for="ingest-placas" class="block text-sm text-slate-700 mb-1">Placas</label>
              <textarea id="ingest-placas" rows="5" bind:value={ingestText} placeholder="ABC1234\nPDM5915\n..." class="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-cyan-500"></textarea>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <button on:click={ingestPlacas} disabled={loadingIngest} class="px-4 py-2 rounded-lg bg-cyan-600 text-white font-semibold hover:bg-cyan-700 disabled:opacity-60">
              {loadingIngest ? 'Registrando...' : 'Registrar placas'}
            </button>
            {#if ingestReport}
              <p class="text-sm text-slate-700">{ingestReport}</p>
            {/if}
          </div>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-4 space-y-4">
          <h3 class="font-semibold text-slate-900">Gestion de usuarios</h3>
          <p class="text-sm text-slate-600">El operador puede crear usuarios y cambiar contraseñas.</p>

          <div class="grid lg:grid-cols-2 gap-4">
            <div class="border border-slate-200 rounded-lg p-3 space-y-3">
              <h4 class="font-semibold text-sm">Crear o actualizar usuario</h4>
              <div>
                <label for="new-username" class="block text-xs text-slate-600 mb-1">Usuario</label>
                <input id="new-username" type="text" bind:value={userForm.username} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
              <div>
                <label for="new-password" class="block text-xs text-slate-600 mb-1">Clave</label>
                <input id="new-password" type="password" bind:value={userForm.password} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
              <div>
                <label for="new-role" class="block text-xs text-slate-600 mb-1">Rol</label>
                <select id="new-role" bind:value={userForm.role} class="w-full border border-slate-300 rounded-lg px-3 py-2">
                  <option value="monitor">monitor</option>
                  <option value="digitador">digitador</option>
                  <option value="operador">operador</option>
                </select>
              </div>
              {#if userForm.role === 'monitor'}
                <div>
                  <label for="new-tag" class="block text-xs text-slate-600 mb-1">Etiqueta monitor</label>
                  <input id="new-tag" type="text" maxlength="2" bind:value={userForm.etiqueta} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
                </div>
              {/if}
              <button on:click={createUser} class="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm">Guardar usuario</button>
            </div>

            <div class="border border-slate-200 rounded-lg p-3 space-y-3">
              <h4 class="font-semibold text-sm">Cambiar contraseña</h4>
              <div>
                <label for="reset-username" class="block text-xs text-slate-600 mb-1">Usuario</label>
                <input id="reset-username" type="text" bind:value={resetTarget} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
              <div>
                <label for="reset-password" class="block text-xs text-slate-600 mb-1">Nueva clave</label>
                <input id="reset-password" type="password" bind:value={resetPasswordValue} class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
              <button on:click={resetPassword} class="px-4 py-2 rounded-lg bg-cyan-700 text-white text-sm">Actualizar clave</button>
            </div>
          </div>

          {#if userActionReport}
            <div class="text-sm rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">{userActionReport}</div>
          {/if}

          <div class="overflow-auto border border-slate-200 rounded-lg">
            {#if loadingUsers}
              <p class="p-3 text-sm text-slate-500">Cargando usuarios...</p>
            {:else}
              <table class="min-w-full text-sm">
                <thead class="bg-slate-50 text-slate-600">
                  <tr>
                    <th class="text-left px-3 py-2">Usuario</th>
                    <th class="text-left px-3 py-2">Rol</th>
                    <th class="text-left px-3 py-2">Etiqueta</th>
                    <th class="text-left px-3 py-2">Activo</th>
                  </tr>
                </thead>
                <tbody>
                  {#each users as u}
                    <tr class="border-t border-slate-100">
                      <td class="px-3 py-2">{u.username}</td>
                      <td class="px-3 py-2">{u.role}</td>
                      <td class="px-3 py-2">{u.etiqueta ? u.etiqueta.toUpperCase() : '-'}</td>
                      <td class="px-3 py-2">{u.active ? 'SI' : 'NO'}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          </div>
        </div>
      {/if}

      {#if !isDigitador()}
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <article class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500">Pendiente</p><p class="text-2xl font-bold">{stats.pendiente}</p></article>
          <article class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500">Solicitada</p><p class="text-2xl font-bold">{stats.solicitada}</p></article>
          <article class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500">Finalizada</p><p class="text-2xl font-bold">{stats.finalizada}</p></article>
          <article class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500">Error</p><p class="text-2xl font-bold">{stats.error}</p></article>
          <article class="bg-white rounded-xl p-4 border border-slate-200"><p class="text-xs text-slate-500">Anulada</p><p class="text-2xl font-bold">{stats.anulada}</p></article>
        </div>
      {/if}

      <div class="bg-white rounded-xl border border-slate-200 p-4">
        <div class="flex flex-wrap gap-2 items-end">
          <div>
            <label for="search-placa" class="block text-xs text-slate-600 mb-1">Buscar placa</label>
            <input id="search-placa" type="text" bind:value={searchPlateInput} on:input={handleSearchInput} placeholder="Ej: PDM5915" class="border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <button on:click={searchByPlate} disabled={loadingSearch} class="px-4 py-2 rounded-lg bg-cyan-700 text-white text-sm disabled:opacity-60">
            {loadingSearch ? 'Buscando...' : 'Buscar'}
          </button>
          <button on:click={clearSearch} class="px-4 py-2 rounded-lg border border-slate-300 text-sm hover:bg-slate-50">Limpiar</button>

          {#if activeSearchPlate}
            <span class="text-xs text-slate-500">Filtro activo: {activeSearchPlate}</span>
          {/if}

          <div class="ml-auto text-xs text-slate-500">
            {totalItems} resultado(s) | Pagina {page} de {totalPages}
          </div>
        </div>

        <div class="flex flex-wrap gap-2 mt-3">
          {#each ['TODAS','PENDIENTE_SOLICITUD','SOLICITADA','FINALIZADA','ERROR','ANULADA'] as estado}
            <button on:click={() => (filtroEstado = estado)} class={`px-3 py-1.5 rounded-lg text-sm border ${filtroEstado === estado ? 'bg-cyan-600 text-white border-cyan-600' : 'bg-white text-slate-700 border-slate-300'}`}>
              {estado}
            </button>
          {/each}
        </div>
      </div>

      {#if isOperador() || isDigitador()}
        <div class="bg-white rounded-xl border border-slate-200 p-4">
          <h3 class="font-semibold text-slate-900 mb-2">Cola actual (top 20)</h3>
          {#if colaActiva.length}
            <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {#each colaActiva as item}
                <div class="text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                  <span class="font-semibold">{item.placa}</span>
                  <span class="text-slate-500"> | {item.etiqueta ? item.etiqueta.toUpperCase() : '-'}</span>
                </div>
              {/each}
            </div>
          {:else}
            <p class="text-sm text-slate-500">No hay placas en cola.</p>
          {/if}
        </div>
      {/if}

      <div class="bg-white rounded-xl border border-slate-200 overflow-auto">
        {#if loadingData}
          <p class="p-6 text-slate-500">Cargando ordenes...</p>
        {:else}
          <table class="min-w-full text-sm">
            <thead class="bg-slate-50 text-slate-600">
              <tr>
                <th class="text-left px-4 py-3">Placa</th>
                {#if !isMonitor()}<th class="text-left px-4 py-3">Orden ANT</th>{/if}
                <th class="text-left px-4 py-3">Estado</th>
                {#if !isMonitor()}<th class="text-left px-4 py-3">Etiqueta</th>{/if}
                <th class="text-left px-4 py-3">Actualizado</th>
              </tr>
            </thead>
            <tbody>
              {#each ordenesFiltradas as o}
                <tr class="border-t border-slate-100">
                  <td class="px-4 py-3 font-semibold">{o.placa}</td>
                  {#if !isMonitor()}<td class="px-4 py-3">{o.numero_orden ?? '-'}</td>{/if}
                  <td class="px-4 py-3"><span class="inline-flex px-2 py-1 rounded-md text-xs bg-slate-100">{o.estado}</span></td>
                  {#if !isMonitor()}<td class="px-4 py-3">{o.etiqueta ? o.etiqueta.toUpperCase() : '-'}</td>{/if}
                  <td class="px-4 py-3">{fmt(o.updated_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <div class="flex items-center justify-center gap-2">
        <button on:click={() => goToPage(page - 1)} disabled={page <= 1 || loadingData} class="px-3 py-1.5 rounded-lg border border-slate-300 text-sm hover:bg-slate-50 disabled:opacity-50">
          Anterior
        </button>
        <span class="text-sm text-slate-600">Pagina {page} / {totalPages}</span>
        <button on:click={() => goToPage(page + 1)} disabled={page >= totalPages || loadingData} class="px-3 py-1.5 rounded-lg border border-slate-300 text-sm hover:bg-slate-50 disabled:opacity-50">
          Siguiente
        </button>
      </div>
    </section>
  </main>
{/if}
