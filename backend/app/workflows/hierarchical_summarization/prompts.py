# Prompt templates - contains LLM prompts for: section summarization (with context preservation), hierarchical merging (with original context augmentation), and final summary generation

MAP_SUMMARIZATION = """Resume la siguiente sección de un RFP. Captura puntos importantes de un RFP a considerar (en caso de que hayan) como ubicaciones, equipos, presupuestos, etc..
Es un resúmen, no una explicación, el objetivo es reducir el tamaño del texto.

Input:
{input_text}

Output:
"""

MAP_SUMMARIZATION_WITH_QUERY = """Resume la siguiente sección de un RFP. Captura puntos importantes de un RFP a considerar (en caso de que hayan) como ubicaciones, equipos, presupuestos, etc..
Es un resúmen, no una explicación, el objetivo es reducir el tamaño del texto.

INSTRUCCIONES ADICIONALES DEL USUARIO:
{user_query}

Input:
{input_text}

Output:
"""

REDUCE_SUMMARIZATION = """Resume y combina los siguientes resúmenes de secciones de un RFP en un solo resumen coherente. Captura todos los puntos importantes mencionados como ubicaciones, equipos, presupuestos, etc.
Es un resúmen consolidado, no una explicación, el objetivo es reducir el tamaño del texto manteniendo la información clave.

Input:
{input_summaries}

Output:
"""

REDUCE_SUMMARIZATION_WITH_QUERY = """Resume y combina los siguientes resúmenes de secciones de un RFP en un solo resumen coherente. Captura todos los puntos importantes mencionados como ubicaciones, equipos, presupuestos, etc.
Es un resúmen consolidado, no una explicación, el objetivo es reducir el tamaño del texto manteniendo la información clave.

INSTRUCCIONES ADICIONALES DEL USUARIO:
{user_query}

Input:
{input_summaries}

Output:
"""

EXECUTIVE_SUMMARIZATION = """Genera un resumen ejecutivo conciso del siguiente documento RFP. Enfócate en los aspectos estratégicos y de negocio más importantes para la toma de decisiones ejecutivas.

El resumen debe ser breve (menos de una página) y cubrir elementos como:

- **Objetivo Principal**: ¿Cuál es el propósito central de esta licitación?
- **Alcance y Requisitos Clave**: ¿Qué se está solicitando? (equipos, servicios, ubicaciones)
- **Presupuesto y Aspectos Financieros**: Montos, formas de pago, garantías
- **Plazos Críticos**: Fechas límite importantes, duración del proyecto
- **Riesgos y Consideraciones**: Restricciones, penalizaciones, requisitos especiales
- **Criterios de Evaluación**: Cómo se evaluarán las propuestas

Dependiendo de la información contenida en el documento, decide sí incluir otros apsectos que consideres importante o excluir algunos de menor importancia o sin información.
Mantén un tono profesional y directo. Prioriza información accionable para ejecutivos que necesitan tomar decisiones rápidas.

Documento:
{input_text}

Resumen Ejecutivo:
"""