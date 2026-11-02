# MessiScript v2

MessiScript es un Lenguaje de Dominio Específico (DSL). Permite programar, compilar y simular jugadas históricas de Lionel Messi.
La versión 2 incluye nuevas estructuras de control (variables y repeticiones) y una interfaz gráfica interactiva (GUI) con un motor de juego en 2D el cual permite visualizar la ejecución del código paso a paso, corregir errores en tiempo real y desbloquear trofeos.

---
Instalación y Uso de la Interfaz Gráfica
La interfaz está construida con Python 3 y PySide6. Para correr el "Modo Carrera" con la cancha 2D, el editor integrado y los trofeos, se deben seguir los siguientes pasos:
1. Preparar el entorno virtual
Es recomendable usar un entorno virtual para instalar las dependencias de la interfaz.
En Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
2. Instalar dependencias
```powershell
pip install -r requirements-ui.txt
```
3. Ejecutar el juego
```powershell
python main.py
```
# Características de la GUI

4 Niveles Históricos: Incluye México 2022, Croacia 2022, Final 2022 y una simulación de Inglaterra 2026.
Editor de Código Integrado: Resaltado de sintaxis, numeración de líneas y subrayado de errores de compilación (click-to-line).
Cancha 2D: Visualización cenital de los pases, movimientos de los jugadores, rivales y remates al arco.
Paneles de Depuración: Tablas con los errores detectados, tabla de símbolos y acciones decodificadas.
Sistema de Trofeos: Desbloqueo de logros que se guardan en tu progreso local.

---
# Uso del Compilador (Modo CLI)
Si solo se quiere usar el analizador léxico/sintáctico por consola (ideal para pruebas rápidas o integración), se puede seguir usando el script original sin necesidad de instalar PySide6.
```powershell
# Analizar un archivo con código MessiScript
python analizar.py ejemplo_v2.messi
```
Uso como API:
```python
from messiscript import analizar

resultado = analizar("""INICIAR CROACIA_2022
VAR PASOS = 2
REPETIR 3 { MOVER DERECHA PASOS }
PASE ALVAREZ
FIN""")

print(resultado)
# Devuelve un JSON con: valido, errores, acciones, simbolos y escenario.
```
> *Nota:* El motor de validación semántica rechaza pases a uno mismo, jugadores que no están en la cancha, o salir de los límites permitidos (máx. 20 pasos, 10 repeticiones, 300 acciones).
---
# Sintaxis de MessiScript v2
El lenguaje es case-sensitive. Todos los comandos deben ir en mayúsculas.
Instrucción / Mejora	Ejemplo de Uso	Descripción
Estructura Base	`INICIAR ESCENARIO` ... `FIN`	Define el contexto/plantel y los límites del programa.
Variables	`VAR PASOS = 2`	Declara constantes enteras (solo al principio). Impacta en la Tabla de Símbolos.
Movimiento	`MOVER DERECHA PASOS` o `MOVER ARRIBA 1`	Desplaza al jugador. Resolución semántica de variables o literales.
Bucle / Repetición	`REPETIR 3 { ... }`	Repite un bloque de instrucciones. Admite anidamiento (gramática recursiva).
Pase	`PASE ALVAREZ`	Comprueba disponibilidad contextual en la tabla del escenario. El control pasa al receptor.
Remate	`REMATAR`	Dispara al arco para finalizar la jugada.
Comentarios	`// linea` o `/* bloque */`	Ignorados por el analizador léxico.

---
# Arquitectura y Separación de Responsabilidades
El proyecto está diseñado de forma modular para respetar los principios del diseño de compiladores:
`messiscript/` (El Compilador): Contiene el `Scanner`, `Parser` y la lógica de validación `semantica.py`. Es 100% independiente de la UI. Analiza el texto y devuelve un AST simplificado (lista de acciones).
`juego/` (El Motor): Escrito en Python puro. Recibe las acciones del compilador y simula la física (colisiones, alcances, intersecciones de pases).
`ui/` (La Interfaz): Construida en PySide6. Solo dibuja frames y captura eventos del usuario. No toma decisiones de reglas de juego ni de compilación.

---
# Estado de Coco/R
Para fines académicos, es importante destacar el flujo de generación:
La versión v1 fue generada exitosamente con `CocoRPy27 1.4.1` bajo Python 2.7. Los archivos originales (`Scanner.py` y `Parser.py`) se conservan en la carpeta `python2_original/` como respaldo histórico.
Los analizadores en la carpeta principal `messiscript/` fueron adaptados para Python 3 y funcionan con la gramática v2. Sin embargo, sus extensiones (para la construcción del AST y soporte de v2) son actualmente parches manuales.
Pendiente para automatización total: Volver a ejecutar CocoRPy27 con `MessiScript.atg`, inyectar las acciones semánticas directamente en el archivo `.atg` y usar un script de transpilación automática a Python 3.
> ⚠️ **No se utilizó ninguna librería externa** (como PLY o ANTLR) como sustituto; el motor subyacente sigue la lógica predictiva descendente originalmente generada por Coco/R.
# Pruebas Automáticas
El proyecto cuenta con una robusta suite de tests que valida tanto el compilador como el motor del juego. Para ejecutarlos:
```powershell
# Pruebas del compilador (Coco/R)
python -m unittest test_messiscript.py -v

# Pruebas del motor y la UI (requiere el entorno virtual activado)
python -m unittest discover -s test -v
```
---
Licencia: Se mantiene `LICENCIA_COCOR.txt` y los encabezados de los archivos del generador original.
