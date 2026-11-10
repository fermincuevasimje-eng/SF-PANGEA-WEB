# Parche de seguridad — rama `seguridad/quitar-secretos-del-codigo`

## Qué se arregló
1. **Atajo de sesión por URL eliminado.** Antes la app marcaba como autenticado a cualquiera que abriera la app con un parámetro en la URL. Ahora siempre pide usuario y contraseña. Lo mismo en el chat: ya no toma el usuario desde la URL.
2. **Contraseñas fuera del código.** El diccionario con las 31 contraseñas ya no está en `app.py`. Ahora se leen de Streamlit Secrets, sección `[users]`. La comparación usa `hmac.compare_digest`.
3. **PINs fuera del código.** `config.py` ya no trae valores. Lee `[pins]` de Secrets y si no hay Secrets, los PINs quedan vacíos y SF6 queda bloqueado (no abierto).
4. **`.gitignore` nuevo:** protege `.streamlit/secrets.toml` para que nunca se suba por accidente.
5. **`.streamlit/secrets.toml.example`:** plantilla con los 31 usuarios y los 2 PINs, con valores de ejemplo que DEBES cambiar.

## Lo que tienes que hacer tú (no lo puedo hacer por ti)
1. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` en tu compu, con contraseñas y PINs NUEVOS y distintos para cada usuario. Las anteriores estaban en un repo público: considéralas comprometidas.
2. En Streamlit Cloud, abre tu app > Settings > Secrets y pega el contenido de tu `secrets.toml` (conservando tus secciones `[supabase]` y `[connections.gsheets]` que ya tenías).
3. Sube esta rama y haz merge: la rama existe solo en mi copia local, así que yo hago el commit y el push cuando me lo apruebes. Tú la revisas en GitHub con un Pull Request, la apruebas y hacemos merge a tu rama principal. No hagas checkout de esta rama en tu compu, porque ahí no existe.
4. **Importante — el historial de Git todavía tiene las contraseñas viejas.** Quitarlas del código actual no las borra del historial. Por eso el paso 1 (cambiarlas todas) no es opcional. Si quieres borrarlas del historial también, hay que reescribirlo con `git filter-repo` o empezar un repo nuevo. Dime y te guío.

## Qué NO cambió
- La pantalla de login es la misma: selector de usuario + contraseña.
- Los nombres de usuario son los mismos 31.
- Los módulos, las Sheets y el chat funcionan igual.
- Nada se subió a GitHub: los cambios están solo en una rama local, listos para que los revises.

## Pendiente para la fase 2
- Migrar a Supabase Auth (usuarios con hash, expiración de sesión, bloqueo por intentos). Este parche quita el riesgo inmediato sin cambiar cómo entra la gente hoy.
- El chat sigue permitiendo elegir usuario sin contraseña una vez dentro de la app; queda cubierto por el login principal, pero la fase 2 lo debe atar a Supabase Auth.
