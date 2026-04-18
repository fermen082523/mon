# 🚀 INICIO RÁPIDO - Dashboard RTV

## Paso 1: Instalar dependencias

```bash
cd e:\gowon\AUTO-RTV\dashboard
npm install
```

## Paso 2: Verificar `.env.local`

El archivo ya tiene las credenciales de Supabase configuradas:

```env
VITE_SUPABASE_URL=https://abucnbuzqlwjvktgcuhe.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_71lmCp-wGVkZH1bhLpWdqw_7f5cSmjM
```

✅ Está listo para usar.

## Paso 3: Iniciar en desarrollo

```bash
npm run dev
```

Se abrirá en [http://localhost:5173](http://localhost:5173)

## Paso 4: Iniciar sesión

Usa cualquier credencial de Supabase Auth registrada en el proyecto.

Si no tienes usuarios, crea uno en Supabase:
1. Ve a https://app.supabase.com
2. Proyecto: AUTO-RTV
3. Authentication → Users → Add user
4. Email y contraseña

## Flujos

### Login
- Página inicial: `/` 
- Mostrada solo si NO hay sesión activa
- Credenciales se validan contra Supabase Auth

### Dashboard
- Ruta protegida: `/dashboard`
- Visible solo con sesión activa
- Mostrará en TIEMPO REAL:
  - Estadísticas (Pendiente, Solicitada, Finalizada, Error, Anulada)
  - Tabla de órdenes con placa, orden ANT, estado, etiqueta
  - Filtros por estado

### Cierre de sesión
- Botón "Salir" en la esquina superior derecha
- Destruye la sesión
- Redirige a login

## Estructura de archivos

```
src/
├── app.css                    # Estilos globales + Tailwind
├── app.html                   # HTML principal
├── lib/
│   ├── supabase.ts           # Cliente Supabase + funciones auth
│   ├── ordenes.ts            # Funciones de consulta de órdenes
│   ├── Header.svelte         # Componente header
│   ├── StatCard.svelte       # Tarjeta de estadística
│   └── OrdenesTable.svelte   # Tabla de órdenes
└── routes/
    ├── +page.svelte          # Login (/)
    ├── +layout.svelte        # Layout protegido
    ├── login.svelte          # (no se usa, está en +page.svelte)
    └── dashboard/
        ├── +layout.svelte    # Header + contenedor
        └── +page.svelte      # Dashboard principal (/dashboard)
```

## Build para producción

```bash
npm run build
npm run preview
```

Output se genera en `dist/`

## Troubleshooting

### "Cannot find module" en Supabase
Verifica que `.env.local` tenga las variables correctas.

### Login no funciona
1. Verifica credenciales en Supabase → Authentication → Users
2. Comprueba que VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY son correctos
3. Abre consola del navegador (F12) para ver errores específicos

### Tabla vacía en dashboard
1. El backend debe haber ejecutado `sync-supabase` para llenar datos iniciales
2. Verifica que las tablas `rtv_ordenes` y `rtv_auditoria` existan en Supabase
3. Revisa que el backend esté sincronizando (heartbeat cada 60s)

### No se actualiza en tiempo real
Svelte está suscrito a cambios con WebSocket. Si no funciona:
1. Verifica en Supabase → Realtime → "rtv_ordenes" está habilitada
2. Recarga la página (Ctrl+Shift+R)

## Próximas mejoras

- [ ] Detalles de orden + auditoría completa
- [ ] Búsqueda y filtros avanzados
- [ ] Gráficos de estado
- [ ] Exportar CSV
- [ ] Dark mode
