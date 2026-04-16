# Checklist de verificación

## 1. Configuración y arquitectura general

- [ ] 1.1 Se creó y compiló correctamente el archivo .proto con definición de servicios y mensajes.
- [ ] 1.2 El servidor inicia correctamente y está preparado para recibir múltiples conexiones.
- [ ] 1.3 El cliente puede conectarse al servidor desde otra máquina o contenedor en red LAN.
- [ ] 1.4 Se utilizó docker-compose para levantar todos los servicios en contenedores.
- [ ] 1.5 Se definió una red Docker compartida para comunicar contenedores.

## 2. Funcionalidad del servidor

- [ ] 2.1 El servidor asigna un identificador único a cada cliente.
- [ ] 2.2 Mantiene el estado global del tablero.
- [ ] 2.3 Controla correctamente el turno.
- [ ] 2.4 Valida jugadas.
- [ ] 2.5 Envía actualizaciones del tablero a todos los clientes (streaming).
- [ ] 2.6 Detecta fin del juego y lo notifica.
- [ ] 2.7 Registra puntuación, tiempos de respuesta y desempeño por partida.

## 3. Funcionalidad del cliente

- [ ] 3.1 Se une con nombre y recibe ID.
- [ ] 3.2 Muestra tablero en consola de forma legible.
- [ ] 3.3 Permite seleccionar dos cartas por turno.
- [ ] 3.4 Valida localmente si es su turno.
- [ ] 3.5 Actualiza tablero al recibir notificaciones.
- [ ] 3.6 Mensajes adecuados (inicio/turno/errores/fin).

## 4. Lógica del tablero

- [ ] 4.1 Genera pares barajados al azar.
- [ ] 4.2 Actualiza estado correctamente al encontrar pareja.
- [ ] 4.3 Diferencia visualmente ocultas/reveladas/emparejadas.
- [ ] 4.4 Respeta reglas: 2 selecciones por turno.

## 5. Documentación y entrega

- [ ] 5.1 Reporte PDF.
- [ ] 5.2 Comentarios descriptivos.
- [ ] 5.3 Arquitectura descrita.
- [ ] 5.4 Componentes relevantes explicados.
- [ ] 5.5 Capturas de pantalla con múltiples clientes.

## 6. Validación final

- [ ] 6.1 Al menos 3 clientes juegan desde equipos distintos.
- [ ] 6.2 Turnos respetados.
- [ ] 6.3 Fin del juego correcto.
- [ ] 6.4 Métricas correctas.
- [ ] 6.5 Consultar partidas almacenadas en el servidor.
