# Guía de Identidad Visual y Sistema de Diseño
## Marca Personal — Desarrollo Web Freelance & Arquitectura de Software

Este documento establece las directrices de diseño, uso de color y jerarquía tipográfica para mantener la coherencia visual en todos los puntos de contacto de la marca: sitio web personal, documentación técnica, propuestas comerciales, interfaces de usuario y plataformas profesionales.

---

## 1. Filosofía de la Identidad Visual

La combinación de colores crudos y tipografía clásica rompe con el estándar de la industria tecnológica (tradicionalmente saturada de tonos azules y neones). Esta identidad se inspira en la estética **editorial, documental y de investigación de alto nivel**. 

Proyecta:
- **Autoridad y Rigor Técnico:** Sistemas estables, documentación meticulosa y metodologías estructuradas.
- **Sofisticación y Confianza:** Enfoque premium alejado de soluciones masivas o parches rápidos.
- **Transparencia y Claridad:** Estructuras limpias que facilitan la lectura de datos complejos.

---

## 2. Paleta de Colores y Matriz de Uso

La paleta se compone de cuatro colores específicos. Cada uno tiene un rol funcional estricto para evitar la contaminación visual.

| Color | Hex | Nombre Conceptual | Rol en el Sistema | Uso Principal |
| :--- | :--- | :--- | :--- | :--- |
| ![#F2F2F2](https://via.placeholder.com/15/F2F2F2/000000?text=+) `#F2F2F2` | `#F2F2F2` | **Nieve Base** | Fondo Principal (Lienzo) | Fondos de página web, cuerpo de documentos técnicos, áreas de lectura masiva. |
| ![#EAE4D5](https://via.placeholder.com/15/EAE4D5/000000?text=+) `#EAE4D5` | `#EAE4D5` | **Arena Caliza** | Superficie Secundaria | Bloques de código, tarjetas de proyectos, fondos de secciones destacadas, contenedores de llamadas a la acción (CTA). |
| ![#B6B09F](https://via.placeholder.com/15/B6B09F/000000?text=+) `#B6B09F` | `#B6B09F` | **Piedra Taupe** | Acento y Atenuación | Bordes sutiles, separadores de secciones, etiquetas de tecnologías (tags), texto secundario o fechas. |
| ![#000000](https://via.placeholder.com/15/000000?text=+) `#000000` | `#000000` | **Negro Absoluto** | Alto Contraste y Tipografía | Títulos principales, texto de cuerpo sobre fondos claros, botones principales (solid backgrounds), headers de documentos premium. |

### Reglas de Aplicación del Color

* **Regla del 60-30-10:** * **60% (Dominante):** `#F2F2F2` (Garantiza legibilidad y limpieza visual).
    * **30% (Secundario):** `#EAE4D5` y `#000000` (Estructura, contenedores y bloques de texto).
    * **10% (Acento):** `#B6B09F` (Detalles, micro-interacciones, divisores).
* **Accesibilidad (WCAG):** El texto en `#000000` debe ser la única opción para párrafos largos sobre fondos `#F2F2F2` o `#EAE4D5`. Evitar usar `#B6B09F` para textos extensos, limitándolo exclusivamente a elementos decorativos, estados desactivados o textos de soporte muy cortos (como subtítulos de un solo renglón).

---

## 3. Sistema Tipográfico

El sistema tipográfico combina la tradición y el carácter de una fuente *Serif* con la versatilidad y limpieza técnica de una *Sans-Serif*.

### 3.1. Títulos: Libre Baskerville (Serif)
Aporta peso institucional, elegancia y un tono de "informe pericial" o documentación de ingeniería clásica.
* **Dónde usar:** Títulos de la web (H1, H2), cabeceras de secciones en propuestas, títulos de módulos en reportes técnicos, citas textuales destacadas.
* **Comportamiento:** Debe usarse con un interlineado (*line-height*) ligeramente ajustado (1.2 - 1.3) y nunca en textos que superen las tres líneas.

### 3.2. Textos y UI: Roboto (Sans-Serif)
Representa la agilidad, la precisión matemática y la claridad del software moderno.
* **Dónde usar:** Párrafos de texto, tablas de bases de datos, documentación técnica, etiquetas de código, menús de navegación, botones y formularios.
* **Comportamiento:** Requiere un interlineado óptimo (1.5 - 1.6) para asegurar que la lectura técnica de arquitecturas de software e infraestructura sea fluida y descanse la vista del cliente.

### 3.3. Escala Tipográfica Recomendada (Web y PDF)

| Elemento | Fuente | Tamaño (Web) | Tamaño (Print/PDF) | Peso (Weight) | Caso de Uso |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **H1** | Libre Baskerville | `2.25rem` (36px) | 24pt | Bold (700) | Títulos principales de páginas o portadas. |
| **H2** | Libre Baskerville | `1.5rem` (24px) | 16pt | Regular (400) / Bold | Títulos de secciones o módulos del sistema. |
| **H3** | Libre Baskerville | `1.25rem` (20px) | 13pt | Italic (400) | Subsecciones o títulos de tarjetas. |
| **Body** | Roboto | `1rem` (16px) | 10.5pt | Regular (400) | Párrafos generales y explicaciones técnicas. |
| **Small / Meta**| Roboto | `0.875rem` (14px) | 9pt | Light (300) / Regular | Fechas, tags de tecnologías, notas al pie. |
| **Code Block** | Monospace / Roboto | `0.9rem` (14px) | 9.5pt | Regular (400) | Fragmentos de código Python, comandos Docker. |

---

## 4. Contextos de Aplicación Práctica

### 4.1. Sitio Web y Portafolio Digital
* **Fondo General:** `#F2F2F2`.
* **Sección Hero:** Título principal en `Libre Baskerville` (`#000000`). Texto introductorio en `Roboto`.
* **Tarjetas de Proyectos (Casos de Estudio):** Fondo de tarjeta en `#EAE4D5`. Bordes finos de 1px en `#B6B09F` para separar los bloques de manera sofisticada. 
* **Botones (CTAs):** Fondo `#000000` con texto en `#F2F2F2` (Estado normal). Al hacer *hover*, el fondo cambia a `#B6B09F` con texto `#000000`.

### 4.2. Documentación Técnica ("Manuales de Vuelo")
Para la entrega de arquitecturas, diagramas de infraestructura o reportes de seguridad:
* **Encabezados de Tabla:** Fondo `#000000` con texto `Roboto` en `#F2F2F2`.
* **Filas Alternas (Zebra Striping):** Alternar entre `#F2F2F2` y `#EAE4D5` para facilitar el análisis visual de métricas o logs.
* **Bloques de Código / Configuración:** Fondo `#EAE4D5` con un borde izquierdo grueso (4px) en `#000000`.

### 4.3. Propuestas Comerciales (Freelance PDF)
* **Portada:** Minimalista. Fondo completo en `#EAE4D5` o `#F2F2F2`. El título del proyecto en tamaño grande con `Libre Baskerville` en `#000000`. Un bloque inferior sólido en `#000000` para los datos de contacto.
* **Páginas Interiores:** Margen amplio. Numeración de páginas y encabezados atenuados utilizando el color `#B6B09F`.

---

## 5. Restricciones de Estilo (Lo que NO se debe hacer)

1.  **Prohibido el uso de colores saturados:** No introducir Azules "Tech", Verdes "Cyber" o Morados en botones o enlaces. Toda la fuerza visual radica en el contraste entre el negro, el beige y la escala de grises claros.
2.  **No invertir la jerarquía tipográfica:** Nunca utilices `Roboto` para los títulos principales ni `Libre Baskerville` para bloques largos de texto corriente. Esto destruiría la legibilidad y el aire editorial.
3.  **Evitar sombras paralelas difusas (Box Shadows pesadas):** Para separar capas visuales, utiliza el color de fondo secundario (`#EAE4D5`) o líneas divisorias delgadas (`1px solid #B6B09F`) en lugar de sombras negras difuminadas. Mantén la estética plana, limpia y arquitectónica.
4.  **No usar texto blanco sobre fondo `#B6B09F`:** No cumple con los estándares mínimos de contraste exigidos para interfaces profesionales.
