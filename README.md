# MessiScript v2 (Python) — ampliacion de Compiladores

Proyecto basado en MessiScript v1. Se preservan `INICIAR`, `MOVER`, `PASE`,
`REMATAR`, `FIN`, los comentarios y la sintaxis previa, y se agregan mejoras
acotadas al lenguaje.

## Ejecutar

No hace falta instalar paquetes adicionales para **usar** el analizador
entregado. Requiere Python 3.

```powershell
py -3 analizar.py ejemplo.messi
py -3 analizar.py ejemplo_v2.messi
py -3 -m unittest -v
```

Alternativamente, reemplazá `py -3` por `python`.

La API también está disponible:

```python
from messiscript import analizar

resultado = analizar("""INICIAR CROACIA_2022
VAR PASOS = 2
REPETIR 3 { MOVER DERECHA PASOS }
PASE ALVAREZ
FIN""")
print(resultado)
```

Devuelve `valido`, `errores`, `acciones`, `simbolos` y `escenario` en programas
sintácticamente válidos; en caso de error léxico/sintáctico solo devuelve
`valido`, `errores` y `acciones` vacío. Las posiciones de error incluyen línea
y columna. La salida es JSON serializable. No ejecuta movimientos reales en
una cancha: `acciones` es una lista ordenada para el futuro simulador.

## Qué cambió

| Mejora | Función | Contenido académico |
|---|---|---|
| `VAR PASOS = 2` | Declara constantes enteras, solo al principio | Identificadores y tabla de símbolos |
| `MOVER DERECHA PASOS` | Usa una constante en un movimiento | Resolución y validación semántica |
| `REPETIR 3 { ... }` | Repite un bloque, admite anidamiento | Gramática recursiva y expansión de instrucciones |
| `PASE ALVAREZ` | Comprueba que esté en el escenario | Análisis semántico contextual |

Se rechazan variables no declaradas o duplicadas, escenarios desconocidos,
jugadores ausentes y cantidades fuera de rango. Los límites de seguridad del
prototipo son **1–20 pasos**, **1–10 repeticiones** y **300 acciones** por
programa. No hay `SI/SINO`, expresiones aritméticas ni asignaciones posteriores:
se dejaron fuera intencionalmente para que el trabajo sea manejable.

Las declaraciones `VAR` se colocan después de `INICIAR ESCENARIO` y antes de la
primera instrucción. Son **constantes enteras** sin modificación posterior.
La gramática exige **al menos una instrucción** en cada bloque.

### Ejemplo v2

```text
INICIAR CROACIA_2022
VAR PASOS = 2
REPETIR 2 {
    MOVER DERECHA PASOS
    MOVER ARRIBA 1
}
PASE ALVAREZ
FIN
```

Salida de acciones (resumen): dos pares de movimientos y finalmente el pase.

## Escenarios

`messiscript/escenarios.json` contiene **planteles de demostración**, no una
reconstrucción exhaustiva o histórica ni las posiciones de los jugadores.
Actualmente se incluyen `CROACIA_2022`, `FINAL_2022` y `MEXICO_2022`.

Al integrar el juego, la API puede recibir sus propios jugadores precargados:

```python
resultado = analizar(
    "INICIAR NIVEL_1 PASE ALVAREZ FIN",
    escenarios={"NIVEL_1": {"jugadores": ["MESSI", "ALVAREZ"]}},
)
```

Esto solo valida **pertenencia al escenario**. La trayectoria del pase, las
colisiones, la posesión y el cumplimiento del objetivo son responsabilidad
del motor de juego, no del parser. El pase a `MESSI` se rechaza porque Messi
es el futbolista controlable en este prototipo.

## Archivos relevantes

- `python2_original/MessiScript.atg`: gramática formal propuesta para v2.
- `python2_original/MessiScript_v1.atg`: gramática original conservada.
- `python2_original/{Scanner,Parser}.py`: **salidas v1** originales de Coco/R
  en Python 2, conservadas como respaldo.
- `messiscript/{Scanner,Parser}.py`: archivos originalmente generados con Coco/R
  para v1 y **ampliados manualmente** para reconocer v2 y construir un AST.
- `messiscript/analizador.py`: API principal, integración del parser y semántica.
- `messiscript/semantica.py`: tabla de símbolos, validaciones y expansión.
- `messiscript/escenarios.json`: configuración de planteles de prueba.
- `ejemplo_v2.messi`: programa de demostración.
- `test_messiscript.py` y `casos_prueba.json`: pruebas automáticas.

## Estado del generador Coco/R — importante para la defensa

La versión v1 **sí fue generada** con CocoRPy27 1.4.1 bajo Python 2.7. El
Scanner y Parser Python 3 de esta entrega **funcionan** y siguen la gramática
v2, pero sus extensiones son **manuales**; no se ejecutó Coco/R para regenerar
los nuevos archivos. No presentarlos como salida recién generada por Coco/R.

Para entregar un proceso totalmente reproducible desde Coco/R, **queda
pendiente** volver a ejecutar CocoRPy27 1.4.1 con `MessiScript.atg` y portar
las acciones de construcción de AST al formato de acciones semánticas del
generador (o instrumentar el nuevo parser). Después se debe reconvertir y
repetir los tests. El archivo `convertir_a_python3.py` se protege contra
sobrescribir la v2 con los analizadores Python 2 **v1** históricos.

No se utilizó una librería externa como sustituto de Coco/R ni se afirma que
este parche manual equivalga a una nueva generación automática.

## Mejoras fuera de alcance

`SI/SINO`, condiciones del entorno, variables reasignables, inferencia de tipos,
animaciones, físicas, adversarios inteligentes y creación dinámica de jugadores.

## Licencia y procedencia

Se mantiene `LICENCIA_COCOR.txt` y los encabezados de los archivos del generador.
Documentación del paquete original: https://pypi.org/project/CocoRPy27/
