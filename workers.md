# Workers de Cloudflare para el tablero

El tablero funciona solo con lo que no necesita proxy (BCRA, data912, argentinadatos, BBVA, Byte, Cocos).
Para el resto hace falta un Worker propio, porque esos sitios no permiten CORS desde otras páginas.
Creá cada Worker en dash.cloudflare.com → Workers & Pages → Create → "Hello World", pegá el código y
copiá la URL (`https://nombre.tu-usuario.workers.dev/`) en el bloque `CFG` al principio del script de `index.html`.

## 1) MAE (`CFG.MAE_WORKER`) — dólar mayorista, caución, gráficos y licitaciones

Una URL, varias rutas: `/FOR`, `/CAU`, `/GRAFICO`, `/LICIT`, `/HISTFOR`, `/HISTCAU`.

```js
const MAE = 'https://api.marketdata.mae.com.ar/api/mercado/';
const RUTAS = {
  FOR: 'datos/FOR',
  CAU: 'datos/CAU',
  GRAFICO: 'titulo/graficoforex',            // ver nota
  LICIT: 'licitacionesporestado/Todos',
  HISTFOR: 'titulo/historicoforex',
  HISTCAU: 'titulo/historicocauciones',
};
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
};
export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const url = new URL(req.url);
    const ruta = RUTAS[url.pathname.replace(/^\//, '')];
    if (!ruta) return new Response('ruta inválida', { status: 404, headers: CORS });
    const r = await fetch(MAE + ruta + url.search, { headers: { Accept: 'application/json' } });
    return new Response(r.body, {
      status: r.status,
      headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    });
  },
};
```

Nota: el endpoint exacto de la ruta `GRAFICO` (serie intradía) lo usa la propia web del MAE; si el mini-gráfico
del día no aparece, abrí marketdata.mae.com.ar con las herramientas de desarrollo del navegador (pestaña Network),
buscá la llamada que trae `precios` con `time` y `value`, y corregí esa línea.

## 2) Plazo fijo online (`CFG.PF_WORKER`)

El tablero espera `{ top10: [...], otros: [...] }`, con cada entrada `{ entidad, codigo, tasa_sin_relacion }`,
armado a partir de https://www.bcra.gob.ar/plazos-fijos-online/ . Hay que leer esa página y convertirla a
ese formato; si querés, pegame el HTML o el JSON de red que usa esa página y te escribo el Worker.

## 3) Cotizaciones por banco (`CFG.REGIONAL_WORKER`, `ICBC_WORKER`, `BNA_WORKER`, `REBA_WORKER`)

Cada Worker lee la cotización oficial de su banco y responde:

- Crédito Regional / ICBC / Banco Nación / Reba: `{ "valorCompra": 1234, "valorVenta": 1260 }`

Los que ya funcionan sin Worker: BBVA, Byte y Cocos. Brubank queda apagado salvo que cargues
`CFG.BRUBANK_URL` con tu propia planilla de Google y tu propia clave.

## Banco resaltado

`CFG.MY_BANK` (por defecto `/cr[eé]dito regional/i`) es la entidad que se marca como "tuya" en plazo fijo y en dólar por entidad.
Cambialo por tu banco, por ejemplo `/galicia/i`.
