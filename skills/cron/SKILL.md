*Sintaxis de Comandos Cron:*
Para programar una tarea, DEBES usar estrictamente el siguiente formato:
`:::cron TIPO MINUTO HORA DIA MES NOMBRE:::`

Donde:
- *TIPO:* `unico` (una sola vez) o `recurrente` (se repite)
- *MINUTO:* 0-59
- *HORA:* 0-23
- *DIA:* 1-31 o `*` para todos los días
- *MES:* 1-12 o `*` para todos los meses
- *NOMBRE:* Descripción de la tarea (puede tener emojis AL FINAL)

El sistema genera AUTOMÁTICAMENTE el notify-send, el echo, y la redirección. Tú SOLO escribes el comando :::cron:::`.

*REGLA DE ORO PARA TIEMPO:*
Siempre recibirás la hora y fecha actual. ÚSALAS.

1. *RECORDATORIOS ÚNICOS* — en X minutos, a las 4pm, mañana:
   - Usa `unico`. Especifica DÍA y MES exactos.
   - Ejemplo si es 10/02/2026 09:35: `:::cron unico 35 9 10 2 Compra de crema y cebolla 🛒:::`

2. *RECORDATORIOS RECURRENTES* — todos los días, cada mes:
   - Usa `recurrente`. Usa `*` en dia/mes según corresponda.
   - Todos los días a las 9: `:::cron recurrente 0 9 * * Despertar ☀️:::`
   - Cada 1° de mes: `:::cron recurrente 0 10 1 * Pagar alquiler 🏠:::`

⛔ *PROHIBIDO:* NO agregues notify-send, echo, ni rutas de archivo. El bot lo hace solo.
✅ BIEN: `:::cron unico 0 15 20 3 Turno médico 🏥:::`
❌ MAL: `:::cron 0 15 20 3 * notify-send "Turno"; echo "Turno" >> eventos.txt:::`

- *NUNCA* uses `*` en minuto Y hora al mismo tiempo (se repite a lo loco).

*Edición y Borrado de Recordatorios*
Ahora tienes la capacidad de *borrar* tareas.
- *Para BORRAR:* Usa `:::cron_delete "TEXTO_UNICO_DE_LA_TAREA":::` donde TEXTO_UNICO es parte del nombre original para identificarlo.
- *Para EDITAR:* Primero borra la tarea antigua y luego crea una nueva en el mismo mensaje.

Ejemplo de Edición:
1. `:::cron_delete "Regar plantas":::`
2. `:::cron recurrente 0 18 * * Regar plantas tarde 🌱:::`

**PALABRAS CLAVE (KEYWORDS para activar esta habilidad):**
recordar, recordatorio, avisar, alarma, rutina, agendar, tarea programada, manana, tarde, noche, recurrentemente, todos los dias, una vez, cron, acuerda, recuerda, notificar.
