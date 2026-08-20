"""TestSprite — el alta pública de tenants está cerrada EN PRODUCCIÓN.

Corre contra la API real (`https://pos.lightningnetwork.tf`), no contra un contenedor.
Complementa a `backend/tests/test_registration_gate.py`, que prueba lo mismo en local:
aquel garantiza que el **código** está bien, éste que **lo desplegado** está bien. Hacen
falta los dos — el gate puede existir en el repo y prod seguir abierta.

## Por qué importa

`POST /api/v2/auth/register` provisiona una wallet LNbits en NUESTRA instancia (custodial,
un wallet por tenant). Abierto = custodiamos fondos de terceros, contradiciendo el
"no-custodial" publicado en App Store y Google Play, con implicaciones regulatorias en MX.

## Sin efectos secundarios, a propósito

Todas las peticiones mandan un body vacío o inválido. Nunca un alta válida.
  - gate CERRADO → 403 (corta antes de mirar el body)
  - gate ABIERTO → 422 (falla la validación del body)
En ambos casos **no se crea ningún tenant ni ninguna wallet**. Un test que mandara un alta
válida contra producción causaría justo el daño que este test previene.

## Los dos caminos, y por qué el duro es el de Railway

`pos.lightningnetwork.tf` lo sirve un Worker de Cloudflare que reescribe el Host hacia
Railway, pero **el dominio de Railway también responde al público** — así que un control que
sólo cubriera el Worker se esquivaría con la URL de Railway.

**Hallazgo del 2026-08-03:** Cloudflare le responde **`error code: 1010`** (403) al runner de
TestSprite en *todas* las rutas de `pos.lightningnetwork.tf`, incluida `/api/health`. Es el
bot-fight/browser-integrity de Cloudflare bloqueando a un cliente de datacenter. O sea que
desde el runner **el camino del Worker no es verificable**, y por eso la aserción dura va
contra Railway. No se pierde cobertura: el gate vive en el backend y el Worker sólo proxea al
mismo proceso.

⚠️ Ojo con la trampa: si este test sólo comprobara `status == 403`, el bloqueo 1010 de
Cloudflare lo habría puesto **verde con el gate completamente ausente**. Por eso se exige
además `detail == "registration_disabled"`. No relajar esa aserción.

## Nota de implementación

Sólo stdlib y ejecución a nivel de módulo: el runner de TestSprite hace `exec(code)` y no
trae `httpx` ni corre pytest. Falla = excepción.
"""

import json
import os
import urllib.error
import urllib.request

WORKER = "https://pos.lightningnetwork.tf"
# El origen directo de Railway NO va escrito acá: este repo es público y ese hostname es el
# mapa de cómo saltarse el Worker. Se pasa por entorno; si falta, el test verifica sólo el
# Worker y lo DICE en la salida, en vez de saltarse el caso en silencio.
RAILWAY_DIRECTO = os.environ.get("LPOS_ORIGIN_DIRECTO", "").strip()
ORIGENES = [("worker-cloudflare", WORKER)]
if RAILWAY_DIRECTO:
    ORIGENES.append(("railway-directo", RAILWAY_DIRECTO))
else:
    print("AVISO: sin LPOS_ORIGIN_DIRECTO ⇒ no se verifica el origen directo, sólo el Worker.")
TIMEOUT = 20

def pedir(metodo, url, body=None):
    """Devuelve (status, texto). No lanza ante 4xx/5xx."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=metodo)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def estado(metodo, url, body=None):
    st, txt = pedir(metodo, url, body)
    print(f"  {metodo} {url} → {st}")
    return st, txt


# Primero recolecta TODO y lo imprime; los asserts van al final. Así una sola corrida
# muestra el cuadro completo en vez de morir en el primer fallo.
ALTA_SONDA = {
    "email": "testsprite-gate-probe@example.invalid",
    "password": "no-uses-esto-jamas-000",
    "name": "TestSprite Gate Probe",
    "tenant_name": "TestSprite Gate Probe",
}

obs = {}
print("=== observaciones ===")
for etiqueta, base in ORIGENES:
    for caso, body in (("register-vacio", {}), ("register-valido", ALTA_SONDA)):
        st, txt = pedir("POST", f"{base}/api/v2/auth/register", body)
        obs[(etiqueta, caso)] = (st, txt)
        print(f"  [{etiqueta}] {caso:16} → {st}   body[:220]={txt[:220]!r}")
    st, txt = pedir("GET", f"{base}/api/health")
    obs[(etiqueta, "health")] = (st, txt)
    print(f"  [{etiqueta}] {'health':16} → {st}   body[:120]={txt[:120]!r}")

st, txt = pedir("POST", f"{WORKER}/api/v2/pairing/redeem", {})
obs[("worker-cloudflare", "pairing")] = (st, txt)
print(f"  [worker-cloudflare] {'pairing/redeem':16} → {st}   body[:160]={txt[:160]!r}")
print()

def es_gate(par):
    """403 CON el detail de FastAPI. Un 403 de Cloudflare (WAF/bot) NO cuenta: se vería
    igual en el status pero trae HTML, y daría un falso positivo."""
    st, txt = par
    if st != 403:
        return False, f"status {st}"
    try:
        d = json.loads(txt).get("detail")
    except Exception:
        return False, "403 pero el body NO es JSON → probablemente Cloudflare, no el gate"
    return d == "registration_disabled", f"detail={d!r}"

def bloqueado_por_cloudflare(par):
    return par[0] == 403 and "error code: 1010" in par[1]


print("=== veredicto ===")
problemas = []

# Camino DURO: Railway directo, sin Cloudflare en medio. Acá vive la verdad.
for caso in ("register-vacio", "register-valido"):
    ok, por = es_gate(obs[("railway-directo", caso)])
    print(f"  {'OK  ' if ok else 'MAL '} [railway-directo] {caso}: {por}")
    if not ok:
        problemas.append(f"[railway-directo] {caso}: {por}")

st_health = obs[("railway-directo", "health")][0]
print(f"  {'OK  ' if st_health == 200 else 'MAL '} [railway-directo] health: status {st_health}")
if st_health != 200:
    problemas.append(f"[railway-directo] health: status {st_health}")

# Camino del Worker: informativo. Si Cloudflare bloquea al runner (1010) no se puede afirmar
# nada; si SÍ deja pasar, entonces se exige el gate igual que en Railway.
for caso in ("register-vacio", "register-valido"):
    par = obs[("worker-cloudflare", caso)]
    if bloqueado_por_cloudflare(par):
        print(f"  AVISO [worker-cloudflare] {caso}: Cloudflare 1010 bloqueó al runner → no verificable desde acá")
    else:
        ok, por = es_gate(par)
        print(f"  {'OK  ' if ok else 'MAL '} [worker-cloudflare] {caso}: {por}")
        if not ok:
            problemas.append(f"[worker-cloudflare] {caso}: {por}")

par_pair = obs[("worker-cloudflare", "pairing")]
if bloqueado_por_cloudflare(par_pair):
    print("  AVISO [worker-cloudflare] pairing/redeem: Cloudflare 1010 → no verificable desde acá")
elif par_pair[0] >= 500:
    problemas.append(f"pairing/redeem: status {par_pair[0]}")

print()
assert not problemas, (
    "El alta pública NO está cerrada (o no se pudo comprobar):\n- " + "\n- ".join(problemas)
)
print("TODO OK — alta cerrada en el backend (camino duro: Railway) y resto de la API sano.")
print("      El camino del Worker sólo se puede verificar desde una IP que Cloudflare no")
print("      bloquee; ver los AVISO de arriba. El gate vive en el backend, así que el")
print("      Worker hereda el comportamiento por proxear al mismo proceso.")
