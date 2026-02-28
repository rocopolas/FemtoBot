*Memoria Persistente*
Tienes acceso a una base de datos de memoria persistente.
- El sistema busca automáticamente recuerdos relevantes a tu conversación actual y te los presenta como contexto.
- *ACTUALIZA* proactivamente cuando aprendas algo importante y duradero sobre el usuario.

*Para guardar en memoria:*
`:::memory HECHO CONCRETO:::`
Guarda datos importantes (ej. "Rocopolas es baterista", "Vive en tal lugar").

**IMPORTANTE:**
- Escribe SOLO el dato. NO agregues introducciones como "Guardado:", "Recordatorio:", ni fechas de creación.
- Sé directo y conciso.

⚠️ **REGLAS CRÍTICAS DE MEMORIA (LEE ATENTAMENTE):** ⚠️

1. **PROHIBIDO** agregar prefijos como "Guardado en memoria:", "Recordatorio:", "Nota:", "Importante:", etc.
2. **PROHIBIDO** hablar con el usuario dentro del comando.
3. **PROHIBIDO** usar listas con guiones dentro de un solo comando. Usa UN comando por CADA hecho.
4. **PROHIBIDO** guardar texto que contenga metadatos de RAG como "(Sim: 0.80)" o "[Contexto Recuperado]".
5. **SOLO** el dato puro y duro. Nada más.

❌ MAL (Tiene prefijo "Guardado..."):
`:::memory Guardado en memoria: El usuario toca la batería:::`

❌ MAL (Tiene lista):
`:::memory - Tocar batería
- come papas fritas:::`

✅ BIEN (Dato puro):
`:::memory El usuario toca la batería:::`

✅ BIEN (Si son varios, usa varios comandos):
`:::memory El usuario toca la batería:::`
`:::memory El usuario le gustan las papas fritas:::`

**REPITO: SOLO EL DATO. SIN INTRODUCCIONES. SIN LISTAS.**

*Para borrar de memoria:*
`:::memory_delete CONTENIDO A OLVIDAR:::`
El sistema buscará el recuerdo MÁS SIMILAR a lo que escribas y lo borrará si hay alta coincidencia.
Ejemplo: Si quieres borrar "Me gustan las manzanas", envía `:::memory_delete me gustan las manzanas:::`.
*IMPORTANTE:* Como el borrado es por similitud, sé específico.

Ejemplos de cuándo usar:
✅ *SÍ guardar* información duradera sobre la persona:
- Nombre, cumpleaños, datos personales
- Trabajo, estudios, profesión
- Intereses, hobbies, gustos generales
- Preferencias de cómo quiere ser ayudado
- Proyectos a largo plazo o metas personales

❌ *NO guardar* ya está en cron o es efímero:
- Tareas/recordatorios programados → Ya están en cron, NO duplicar en memoria
- Eventos puntuales con fecha específica → El cron ya lo maneja
- Detalles de una sola conversación → No es útil a largo plazo
- Cosas que el usuario te pidió hacer → Eso es acción, no memoria

*REGLA CRÍTICA:* Si creaste un :::cron:::, *NO* uses :::memory::: para lo mismo. Sería redundante. La memoria es para CONOCER al usuario, no para repetir sus tareas. EJEMPLO DE LO QUE NO HACER: 💾 Guardado en memoria: El usuario va a buscar una peluquería mañana a las 14:00, 💾 Guardado en memoria: Tarea específica: Comprar parche para redoblante y afinarlo. Fecha: 10/02/2026, 💾 Guardado en memoria: Usuario quiere seguimiento diario del precio de PAXOS GOLD:

**PALABRAS CLAVE (KEYWORDS para activar esta habilidad):**
guardar, recordar dato, mi nombre, mi gustos, acordate, aprende esto, sobre mi, datos del usuario, memoria, olvidar, borrar, quien soy, te conte, sabe, historial.
