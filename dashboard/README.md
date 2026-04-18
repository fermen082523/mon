# RTV Dashboard

Dashboard moderno en **Svelte** para monitoreo en tiempo real de inspecciones vehiculares. Conectado a **Supabase** con autenticación obligatoria.

## Características

✨ **Login requerido** — Acceso seguro con credenciales de Supabase  
📊 **Dashboard en tiempo real** — Estadísticas y tabla de órdenes actualizándose automáticamente  
🎯 **Filtrado por estado** — Visualiza PENDIENTE_SOLICITUD, SOLICITADA, FINALIZADA, ERROR, ANULADA  
🏷️ **Etiquetas** — Visualiza responsables (etiqueta de 2 letras por orden)  
📱 **Responsive** — Diseño mobile-first con Tailwind CSS  

## Instalación

```bash
cd dashboard
npm install
```

## Variables de entorno

El archivo `.env.local` ya contiene las credenciales de Supabase conectadas al proyecto ANT-RTV:

```env
VITE_SUPABASE_URL=https://abucnbuzqlwjvktgcuhe.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_71lmCp-wGVkZH1bhLpWdqw_7f5cSmjM
```

Si usas otro proyecto, actualiza `.env.local` con tus credenciales.

## Ejecución

### Desarrollo
```bash
npm run dev
```
Abre el navegador en [http://localhost:5173](http://localhost:5173)

### Build para producción
```bash
npm run build
npm run preview
```

## Flujo de autenticación

1. Usuario llega a `/` (login)
2. Ingresa email + contraseña
3. Si valida en Supabase, redirige a `/dashboard`
4. Dashboard suscrito a cambios en tiempo real de tabla `rtv_ordenes`
5. Botón "Salir" destruye sesión y vuelve a login

## API de datos

El dashboard consulta directamente de Supabase:

- **rtv_ordenes** — Todas las órdenes con estado, etiqueta, placa, etc.
- **rtv_auditoria** — Auditoría de cambios (no mostrada en dashboard aún)

Tablas y schema usadas:
```sql
CREATE TABLE rtv_ordenes (
  local_id bigint PRIMARY KEY,
  placa text,
  numero_orden text,
  estado text,
  etiqueta text,
  created_at text,
  updated_at text,
  finalizar_after text,
  ...
);
```

## Componentes

- **Header.svelte** — Barra superior con logo, usuario y botón salir
- **StatCard.svelte** — Tarjeta de estadística (pendiente, solicitada, etc.)
- **OrdenesTable.svelte** — Tabla de órdenes filtrable

## Estructura de rutas

```
src/routes/
├── +page.svelte          → Login (/)
├── +layout.svelte        → Layout protegido (requiere sesión)
└── dashboard/
    ├── +layout.svelte    → Header + contenedor
    └── +page.svelte      → Dashboard principal (/dashboard)
```

## Credenciales demo

Cualquier usuario registrado en Supabase puede iniciar sesión. Crea uno en el panel de Supabase Auth.

## Notas

- Los datos se sincronizan con run-loop del backend cada 60 segundos
- El dashboard se suscribe a cambios en tiempo real (WebSocket)
- Los filtros no persisten (se reinician al recargar)

## Próximos pasos

- [ ] Ver detalles de orden + auditoría completa
- [ ] Gráficos de tendencia por etiqueta y estado
- [ ] Búsqueda de placas
- [ ] Exportar reportes CSV
- [ ] Dark mode
