# infra/

## El Worker de Cloudflare NO está en este repo (a propósito)

`pos.lightningnetwork.tf` lo sirve un Worker de Cloudflare (`lpos-proxy`, cuenta `cf-cldflr`,
zona `lightningnetwork.tf`) que reescribe la cabecera `Host` hacia el servicio de Railway. **El
punto de control del ruteo es el `ORIGIN` de ese Worker**, no el custom domain de Railway: en
cada rotación de cuenta se cambia ahí y se redespliega.

Su código **vivía acá** (`infra/cf-proxy-worker.js`) y se movió el **2026-08-20** al hub
privado del owner:

```
<hub>/shared/infra/workers/lpos-proxy.cf-worker.js
```

**Por qué:** este repositorio es **público**, y ese archivo contiene el hostname del origen en
Railway — es decir, el mapa de cómo saltarse el Worker y pegarle al origen directo. Decisión
del owner: no publicarlo.

Matiz honesto, para que nadie crea que esto cierra algo que no cierra: **el origen ya es
alcanzable públicamente** sin credenciales. Esconder el hostname reduce que sea fácil de
encontrar, no la exposición. Cerrarla de verdad requiere red privada de Railway o un secreto
compartido entre el Worker y el origen — trabajo aparte, todavía pendiente.

## Cómo se publica este repo

El repo canónico es **Gitea** (privado). El de GitHub es **público y NO es un mirror**: se
publica como **snapshots squasheados**, un commit por publicación, con la infra excluida por
construcción. Detalle del procedimiento en el `CLAUDE.md` de este repo.
