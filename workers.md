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

El BCRA publica los datos en `https://www.bcra.gob.ar/api/endpoints/plazos-fijos.php` con el formato que ya espera el tablero
(`top10`, `otros`, y en cada entidad `entidad`, `codigo`, `tasa_sin_relacion`). El Worker `bancos` (sección 3) lo reenvía con CORS en la ruta `/pf`:

```js
PF_WORKER:'https://bancos.tu-usuario.workers.dev/pf',
```

## 3) Worker `bancos`: Reba, Banco Nación, ICBC y plazo fijo (`CFG.REBA_WORKER`, `CFG.BNA_WORKER`, `CFG.ICBC_WORKER`, `CFG.PF_WORKER`)

Un solo Worker (por ejemplo `bancos`) con cuatro rutas: `/reba`, `/bna`, `/icbc` y `/pf`. Lee la página pública de cada banco y devuelve
`{ "valorCompra": ..., "valorVenta": ..., "fecha": ... }`. En `index.html` van así (el Worker es el mismo, cambia la ruta final):

```js
REBA_WORKER:'https://bancos.tu-usuario.workers.dev/reba',
BNA_WORKER:'https://bancos.tu-usuario.workers.dev/bna',
ICBC_WORKER:'https://bancos.tu-usuario.workers.dev/icbc',
```

```js
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, OPTIONS' };
const UA = 'Mozilla/5.0 (compatible; tablero-mercados)';
// Rutas que ya devuelven JSON: solo se reenvían con CORS
const JSON_DIRECTO = {
  pf: 'https://www.bcra.gob.ar/api/endpoints/plazos-fijos.php',
  icbc: 'https://www.icbc.com.ar/ICBC_CotizacionMonedaWEB/cotizacion/dolar',
};

const texto = (html) => html
  .replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ');

// "1.535,00" -> 1535 ; "1485,00" -> 1485 ; "1509.0000" -> 1509
const num = (s) => {
  s = String(s).trim();
  if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
  return parseFloat(s);
};

const FUENTES = {
  reba: {
    url: 'https://www.reba.com.ar/dolar-oficial/',
    parse(t) {
      const i = t.search(/Cotizaci[oó]n\s+D[oó]lar/i);
      const s = i >= 0 ? t.slice(i, i + 800) : t;
      const c = s.match(/Compra\s*\$?\s*([\d.,]+)/i);
      const v = s.match(/Venta\s*\$?\s*([\d.,]+)/i);
      if (!c || !v) throw new Error('no se encontró compra/venta');
      return { valorCompra: num(c[1]), valorVenta: num(v[1]) };
    },
  },
  bna: {
    url: 'https://www.bna.com.ar/Personas',
    parse(t) {
      // primera tabla "Cotización Billetes", fila "Dolar U.S.A"
      const m = t.match(/Cotizaci[oó]n\s+Billetes[\s\S]*?Dolar\s+U\.?S\.?A\.?\s+([\d.,]+)\s+([\d.,]+)/i);
      if (!m) throw new Error('no se encontró la fila del dólar');
      const f = t.match(/(\d{2}\/\d{2}\/\d{4})/);
      return { valorCompra: num(m[1]), valorVenta: num(m[2]), fecha: f ? f[1] : null };
    },
  },
};

export default {
  async fetch(req) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const ruta = new URL(req.url).pathname.replace(/^\//, '');
    if (JSON_DIRECTO[ruta]) {
      try {
        const r = await fetch(JSON_DIRECTO[ruta], { headers: { 'User-Agent': UA, Accept: 'application/json' }, cf: { cacheTtl: 60 } });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return new Response(r.body, { headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e.message || e) }), {
          status: 502, headers: { ...CORS, 'Content-Type': 'application/json' },
        });
      }
    }
    const fuente = FUENTES[ruta];
    if (!fuente) return new Response('ruta inválida', { status: 404, headers: CORS });
    try {
      const r = await fetch(fuente.url, { headers: { 'User-Agent': UA }, cf: { cacheTtl: 60 } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = fuente.parse(texto(await r.text()));
      if (!(d.valorCompra > 0 && d.valorVenta > 0)) throw new Error('valores inválidos');
      return new Response(JSON.stringify(d), {
        headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e.message || e) }), {
        status: 502, headers: { ...CORS, 'Content-Type': 'application/json' },
      });
    }
  },
};
```

Probalo abriendo `https://bancos.tu-usuario.workers.dev/reba` y `/bna` en el navegador: tienen que mostrar un JSON con compra y venta.
Escribí este código a partir de cómo se ve el texto de cada página, sin poder bajar su HTML real, así que puede necesitar un ajuste.
Si alguna ruta devuelve un error, pegame el mensaje.

### Brubank

No usa Worker: el tablero consulta directo la planilla de Google que usa la propia web de Brubank (celdas A1 y B1), con la clave pública
que esa web tiene incrustada (`CFG.BRUBANK_URL`). Es una planilla y una clave de Brubank, no tuyas: si ellos las cambian o las restringen,
la fila de Brubank se queda sin datos.

## Banco resaltado

`CFG.MY_BANK` (por defecto `/cr[eé]dito regional/i`) es la entidad que se marca como "tuya" en el ranking de plazo fijo.
Cambialo por tu banco, por ejemplo `/galicia/i`.

Los que ya funcionan sin Worker: BBVA, Byte y Cocos.
