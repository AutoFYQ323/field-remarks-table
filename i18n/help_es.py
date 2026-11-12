# -*- coding: utf-8 -*-
"""Spanish help. Five pages, same order as the Chinese and English help."""

PAGES = (
    (
        "Tabla de atributos",
        """
<h3>Qué hace</h3>
<p>Es una tabla junto a la tabla de atributos de QGIS. No sustituye F6 ni usa su atajo.
Sirve para ver y editar una capa vectorial: ordenar, filtrar, fijar una columna, rellenar valores, pegar por identificador y exportar.
Las notas de campos, los ajustes, la copia de campos y la dirección de líneas tienen cada una su página.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b>: botón de la barra, <b>Vectorial → Field Remarks Table</b>, o el menú contextual de la capa. Primero seleccione una capa vectorial en el panel de capas.</li>
<li><b>Idioma</b>: botón de idioma de la barra. La primera vez sigue el idioma de QGIS y, si no hay, el del sistema; después se recuerda la elección. Hay chino, inglés, español, francés, árabe, alemán, japonés y coreano, y en el menú cada idioma aparece escrito en su propio idioma. Al cambiar, las ventanas ya abiertas de este complemento pasan a ese idioma. En árabe, los botones y títulos van de derecha a izquierda. Los valores de la tabla siguen de izquierda a derecha.</li>
<li><b>Doble clic en el número de fila</b>: selecciona el elemento y acerca el mapa.</li>
<li><b>Clic en el título de columna</b>: ordena. El texto que parece un número se ordena como número.</li>
<li><b>Después de ordenar</b>, la barra de estado muestra el total filtrado y el total completo de las columnas numéricas. Las demás buscan duplicados, sin distinguir mayúsculas.</li>
<li><b>Seleccionar celdas</b>. Al cabo de medio segundo, el mismo sitio muestra cantidad y suma si son números, o duplicados en otro caso.</li>
<li><b>Clic derecho en el título</b>: copiar la columna, copiar con encabezado, copiar para devolver, pegar en la columna, valores únicos, seleccionar duplicados, seleccionar vacíos o editar notas. La copia para devolver lleva el identificador en la columna 1 (el encabezado empieza por #fid). Solo se edita la columna 2. Se escribe por identificador, no por posición. Las fechas se copian como 2024-09-01.</li>
<li><b>Clic derecho en el número de fila</b>: selecciona filas visibles, por ejemplo 10-50, 1-20,35 o 80- hasta la última.</li>
<li><b>Arrastrar una columna</b> solo cambia el orden en esta ventana. El orden de campos de la capa no cambia. Al cerrar no se recuerda.</li>
<li><b>Barra superior, de izquierda a derecha</b>: fijar, ámbito, congelar, filtro de categoría o campo, filtro de texto. El pin azul sigue la capa actual de la leyenda. El pin rojo mantiene esta capa. El ámbito puede ser todos los elementos, la selección, lo visible en el mapa o lo modificado en esta edición. Congelar deja una columna a la izquierda y alinea las filas. El filtro tiene dos listas: categoría o campo a la izquierda, y valores a la derecha (basta uno marcado). El primer valor de la derecha, Todos, no añade filtro. El texto filtra al escribir, tras medio segundo. Los dos filtros actúan a la vez.</li>
<li><b>Cambios sin guardar</b>: la celda queda en amarillo claro. Cerrar la ventana no pregunta otra vez. Guardar y deshacer siguen en QGIS.</li>
<li><b>Comprobación al escribir</b>: edición manual, relleno, inserción rápida y pegado se comprueban según el tipo de campo. Lo que no cabe se omite. Un decimal en un entero se redondea. Un texto demasiado largo se lista antes de confirmar. Los campos de expresión y las uniones no editables son de solo lectura.</li>
<li><b>Relleno</b> (solo en edición): constante, número alrededor del texto, texto añadido, expresión y reemplazo. Puede actualizar las filas filtradas o la selección. Una constante puede ser el nombre de otro campo, y entonces se copia esa columna. Para escribir un texto igual al nombre de un campo, póngalo entre comillas simples. El número alrededor del texto se pone delante o detrás y conserva el texto. El ancho puede ser sin ceros, automático o fijo. Los ceros solo se guardan en campos de texto. Una celda vacía recibe solo el número. El texto añadido solo cambia lo que ya tiene texto. La expresión es una expresión de QGIS. El reemplazo tiene tres modos y, por defecto, es estándar con una constante. Estándar cambia solo el texto encontrado, todas las veces en la celda. Alrededor del hallazgo inserta antes o después y conserva el original. Campo completo sustituye toda la celda si hay coincidencia. Se puede escribir una constante o una expresión por elemento. Las tres formas están en una casilla. Distingue mayúsculas y es parcial, salvo que encienda el icono de coincidencia completa. Las celdas vacías no entran. Una constante vacía borra el texto encontrado.</li>
<li><b>Expresiones guardadas</b>: con Relleno en Expresión aparece un icono de lista a la derecha de ε. Permite añadir, editar, anotar, eliminar y ordenar expresiones guardadas, y abrir una en el generador de expresiones de QGIS. Tras una breve pausa, al escribir se listan las expresiones guardadas que coinciden. La flecha de la derecha lista todas. Doble clic selecciona todo el texto y arrastrar selecciona un trozo. La casilla sigue siendo de texto. Un elemento elegido se ve como «nota» expresión, por ejemplo «Longitud» $length o «FYQ» round( $length / 1000, 2 ). Solo se ejecuta lo que va tras »: cámbielo a round( $length / 1000, 4 ) en la casilla y se ejecuta eso, mientras lo guardado no cambia. El texto que no empieza por «…» se ejecuta tal cual. La casilla de escritura de Reemplazar tiene la misma lista cuando escribe una expresión.</li>
<li><b>Método de relleno por defecto</b>: en Ajustes → Parámetros elija con qué método empieza la barra de relleno: Recordar el último (por defecto; sigue cada cambio que haga), o siempre Constante, Número alrededor del texto, Añadir texto, Expresión o Reemplazar.</li>
<li><b>Seleccionar todo / invertir / quitar selección</b>: las dos primeras actúan sobre las filas de esta tabla. Quitar selección vacía la selección de la capa.</li>
<li><b>Ancho de columna</b>: Ajustar reparte las columnas en la ventana. Completo las abre según el contenido y puede pasar el borde. Aún se puede arrastrar.</li>
<li><b>Copiar, cortar, pegar</b>: Ctrl+C copia las celdas seleccionadas. Copiar de la barra copia elementos enteros. Para editar y devolver: Copiar columna (ida y vuelta). No cambie la columna #fid. Si los identificadores no coinciden, se repiten o la columna de valores está vacía, no se escribe nada.</li>
<li><b>Exportar</b>: CSV puede escribir el texto numérico como número.</li>
<li><b>Gestión de campos</b>: crear, borrar y renombrar. Si el paquete actual aún tiene nombre o significados para ese campo, al borrarlo pregunta si también se borra la nota.</li>
<li><b>Título de la ventana</b>: nombre de la capa - sistema de coordenadas - estado de edición. El sistema prefiere un código EPSG. El estado es solo lectura, en edición, o en edición con cambios sin guardar y cuántos.</li>
<li><b>Barra de estado</b>: tres partes fijas. El 40 % izquierdo es total, mostradas, seleccionadas y orden. El 20 % central es la longitud de línea (capa de líneas, si se activa en Parámetros), calculada desde la geometría, nunca desde un campo. El 40 % derecho es el total de la selección o las estadísticas de columna. Los tres números van en negrita y en negro. Si las mostradas o las seleccionadas no coinciden con el total, solo ese número pasa a rojo. El número de la longitud y los números del resumen de duplicados también van en negrita. Si la ventana es estrecha, cada parte muestra solo lo que cabe.</li>
<li><b>Ajustes</b>: el engranaje del extremo derecho. Tres pestañas: Barra de herramientas, Atajos y Parámetros. Todo se recuerda en este equipo.</li>
<li><b>Estilo</b>: predeterminado, rosa sakura o menta. Lo siguen todas las ventanas de este complemento. Se recuerda en este equipo.</li>
<li><b>Tamaño de la ventana</b>: se recuerda mientras esta sesión de QGIS sigue abierta.</li>
</ul>
""",
    ),
    (
        "Notas de campos",
        """
<h3>Qué hace</h3>
<p>Las notas de campos son la función principal. Un paquete guarda, para capas vectoriales, un nombre visible, una nota al pasar el ratón, significados que se pueden insertar y variables del paquete.
Los paquetes se guardan en este equipo y los comparten todos los proyectos. No van dentro de un .qgz. Las capas y los campos se emparejan por nombre, no por el identificador interno de QGIS.</p>
<p>Con el paquete activado, la cabecera muestra el nombre visible encima del nombre del campo. Al pasar el ratón se ven el nombre, la nota y los significados. Si eso existe, el ratón ya no se queda solo con el nombre del campo.
Si el paquete está apagado, la tabla se edita como siempre y no aplica esta configuración. La tabla de QGIS (F6) no cambia.</p>
<p><b>Mostrar y escribir son cosas distintas.</b> El nombre visible y la nota solo se leen. No se escriben en el elemento. Lo que se escribe es la constante o la expresión del significado.
En un campo con mapa de valores, el valor guardado sigue siendo el código. Aquí se edita el texto que se ve al lado.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>La primera vez</b>: abra la tabla y pulse Notas de campos. En Paquetes, cree uno y selecciónelo. La lista del paquete actual se abre al ancho del nombre. El paquete de reserva no se puede editar. Elija la capa en la leyenda, pulse un campo a la izquierda, escriba el nombre y los significados, y pulse Activar.</li>
<li><b>Ayuda</b>: a la derecha del paquete actual, Ayuda abre esta misma página, la de Notas de campos del menú Ayuda de la barra.</li>
<li><b>Color del icono</b>: el botón solo abre la ventana. No es el interruptor. En color, hay un paquete real seleccionado y activado. En gris, está el paquete de reserva o aún no se ha activado.</li>
<li><b>Paquete de reserva</b>: cada vez que se abre QGIS se empieza en Predeterminado (bloqueado). No se edita, no se activa y no tiene variables. Mientras QGIS sigue abierto se recuerda el paquete elegido. Al salir se vuelve al de reserva. El paquete que creó sigue ahí: selecciónelo y actívelo otra vez.</li>
<li><b>Paquetes</b>: nuevo, borrar y renombrar. El nombre no puede repetirse ni ser el de reserva. Borrar el paquete borra esa configuración. No cambia los elementos de la capa.</li>
<li><b>Activar</b> aplica el paquete a los campos y comprueba que los nombres de capa y campo existan en este proyecto. Si no coinciden, se abre el emparejamiento para señalar el nombre actual. Abrir la ventana, cambiar de paquete o ver la vista previa no abre el emparejamiento. Al cambiar de paquete se desactiva, y hay que activar de nuevo.</li>
<li><b>Si los nombres no coinciden</b>: se puede copiar a un paquete nuevo y luego emparejar. La copia tira las capas y campos que no existen en este proyecto. El paquete original no se toca. También se puede emparejar sin copiar.</li>
<li><b>Editar campos</b>: la lista es la capa actual de la leyenda. El último elemento es el nombre de la capa. Hasta activar, la lista es de solo lectura. Un campo tiene nombre visible, nota y significados. El nombre de capa solo tiene nombre visible y nota para la leyenda. No tiene significados y no se escribe en los atributos.</li>
<li><b>Significados</b>: una fila es una opción para insertar. Doble clic para cambiar la descripción. El valor puede ser una constante o una expresión de QGIS pegada. Una constante puede incluir una variable, por ejemplo {{ciudad}}123. La expresión se calcula en cada elemento. Si un elemento falla, se omite y los demás se escriben. La lista solo muestra los significados de ese campo. Las variables no se vierten solas en cada columna.</li>
<li><b>Mapa de valores</b>: un campo que ya tiene mapa de valores en QGIS se marca en verde. Esas filas vienen de QGIS y no se borran. El texto que va después de «era» es la descripción original. Restaurar predeterminado vuelve a esa descripción. Se edita el texto que ve la gente. La celda sigue guardando el código. En esta tabla también se puede elegir la descripción en una lista. Lo escrito sigue siendo el código.</li>
<li><b>Valor / nota</b> es el botón de la barra. Valor muestra lo guardado. Nota muestra la descripción cuando existe. En modo nota, el filtro de texto también busca descripciones. El botón cambia lo que se ve, no lo ya guardado.</li>
<li><b>Variables</b>: junto a Activar, y pertenecen a este paquete, no a todo QGIS. El título es para leerlo. El contenido es lo que se sustituye. El paquete de reserva no tiene. Al añadir un significado, Insertar variable pone {{título}} en el valor. Se puede añadir texto fijo al lado. La sustitución ocurre al insertar. Cambiar la variable después no reescribe lo ya guardado, y no hay que editar el significado. Si falta el título, se avisa y no se escribe un vacío.</li>
<li><b>Inserción rápida</b>: aparece sobre la tabla cuando las notas están activas y la capa está en edición. Las listas se alinean con las columnas. Tras elegir un significado: actualizar todo, las filas filtradas, la selección, o cancelar. Cancelar conserva la elección para escribirla con la barra de relleno. Una constante escribe el texto ya resuelto. Una expresión se calcula por elemento.</li>
<li><b>Barra de relleno</b>: la inserción rápida usa significados ya configurados. La barra también puede escribir una constante, un número alrededor del texto, texto añadido, una expresión o un reemplazo sin paquete de notas. Las dos necesitan el modo de edición. Guarde desde este complemento o desde QGIS para que llegue al archivo.</li>
<li><b>Vista previa</b>: solo lectura de capas, campos, significados y variables de este paquete. En rojo, lo que no coincide con este proyecto. Por defecto solo se listan las diferencias.</li>
<li><b>Importar / Exportar</b>: se pueden marcar varios paquetes. Un JSON puede llevar varios, variables incluidas. Si el nombre choca, se elige sobrescribir o cambiar el nombre. Importar no activa el paquete. Selecciónelo y pulse Activar.</li>
<li><b>Actualizar</b>: si otra ventana de QGIS cambió los mismos paquetes, pulse Actualizar o pulse esta ventana. No hace falta reiniciar.</li>
<li><b>Al borrar un campo</b>: si Gestión de campos borra un campo que aún tiene nombre, nota o significados en el paquete, pregunta si se borra también la nota. Si se conserva, sigue en el paquete. Un campo posterior con el mismo nombre en esa capa la vuelve a recibir.</li>
</ul>
<h3>Un montaje práctico</h3>
<ul>
<li>Un paquete por trabajo, por ejemplo una ruta o un distrito. Mezclar capas sin relación dificulta el emparejamiento.</li>
<li>Nombre visible corto y la regla en la nota. El texto fijo que se repite va en significados. Los nombres y números que cambian en cada trabajo van en variables.</li>
<li>Defina primero en QGIS los códigos y las descripciones del mapa de valores. Aquí solo se ajusta la descripción que ve la gente.</li>
<li>Al abrir otro proyecto, si la línea de estado dice que capas o campos no coinciden, compruebe que eligió el paquete correcto. Si sí lo quiere, pulse Activar y empareje los nombres.</li>
</ul>
""",
    ),
    (
        "Ajustes",
        """
<h3>Qué hace</h3>
<p>Los Ajustes, el engranaje del extremo derecho de la barra, reúnen tres cosas: qué botones se muestran y en qué orden, un atajo de teclado para cada herramienta y los parámetros de ejecución. Todo se guarda solo en este equipo.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Barra de herramientas</b>: arrastre para reordenar; los separadores también se arrastran. Desmarcar un botón lo oculta y conserva su puesto. Insertar separador añade uno tras la fila actual. Restaurar predeterminado devuelve la disposición inicial.</li>
<li><b>Atajos</b>: una fila por herramienta. Pulse en la casilla y presione una combinación para grabarla; Retroceso o Supr la borra. Solo responden dentro de la ventana de QGIS; no son globales. Una combinación ya usada por otra fila, por una tecla fija de la tabla (copiar celdas, cortar, pegar) o por otra función de QGIS se rechaza y se dice quién la ocupa. Con la tabla cerrada, pulsar el atajo en la ventana principal de QGIS abre primero la tabla y luego ejecuta la herramienta. Borrar todo vacía todas las grabaciones.</li>
<li><b>Parámetros</b>:
«Mostrar la longitud de línea de las entidades seleccionadas»: en capas de líneas, el centro inferior de la ventana de la tabla muestra la longitud total de las entidades seleccionadas. Se calcula desde la geometría, nunca desde un campo. Desactivado por defecto.
«El filtro sigue el campo actual»: en capas no categorizadas, la Filtración cambia a la columna que pulse (los valores marcados vuelven a Todos); las capas categorizadas se quedan en el filtro por categoría. Activado por defecto.
«Límite de valores del filtro rápido»: cuántos valores distintos lista la caja de Filtrar como máximo. Si hay más, solo se muestran los primeros.
«Tolerancia de ajuste del control de dirección (m)»: los extremos solo cuentan como conectados dentro de esta distancia. El valor por defecto es 0.6. La casilla de tolerancia de la ventana de dirección sigue este valor.
«Encabezados de columna»: Solo nombre de campo (el nombre de la fuente de datos), Alias primero (el alias o el nombre visible de la nota de campo si existe; si no, el nombre del campo) o Alias y nombre de campo (dos líneas, por defecto).
«Método de relleno por defecto (edición)»: Recordar el último (por defecto) o uno de Constante, Número alrededor del texto, Añadir texto, Expresión, Reemplazar.</li>
</ul>
""",
    ),
    (
        "Copia de campos",
        """
<h3>Qué hace</h3>
<p>Copia elementos de una capa vectorial a otra y escribe los atributos con el mapa de campos que indique.
Los tipos de geometría deben coincidir. Origen y destino no pueden ser la misma capa. Si el sistema de coordenadas es distinto, se puede reproyectar.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b> desde Copia de campos en la barra de la tabla. La ventana puede quedarse abierta. Al cambiar de idioma, sus rótulos se actualizan al momento.</li>
<li><b>Capas</b>: origen en la primera fila, destino en la segunda. Filtre las listas por punto, línea o polígono. El origen puede cargarse desde un archivo vectorial que QGIS abra, o con «Cargar del portapapeles»: primero use en el proyecto origen Editar → Copiar entidades de QGIS, luego pulse el botón, elija el CRS de origen y se crea una capa temporal que queda como origen.</li>
<li><b>Campos</b>: cada fila es un campo de destino. Elija el campo de origen a la derecha. Emparejar nombres iguales rellena las parejas únicas. El emparejamiento aproximado ignora espacios y guiones bajos, y solo rellena si la pareja es única. Ocultar campos de origen ya usados los quita de las otras listas. Desactívelo para asignar un mismo origen a varios destinos. Las repeticiones se marcan en rojo.</li>
<li><b>Opciones</b>: copiar solo los elementos seleccionados en el origen. Si los sistemas de coordenadas difieren, la reproyección al destino está activada por defecto.</li>
<li><b>Copiar ahora</b> escribe en el búfer de edición del destino. Guarde las ediciones del destino para que queden en el archivo.</li>
<li><b>Guardar</b> conserva el mapa de campos en este equipo para la próxima vez que abra este par de capas.</li>
</ul>
""",
    ),
    (
        "Dirección de líneas",
        """
<h3>Qué hace</h3>
<p>El recorrido sale a la vez desde todos los puntos de la capa de inicio, sigue las líneas conectadas, encuentra las que están digitalizadas al revés y les da la vuelta al orden de vértices.
Ya no hay que elegir un solo inicio: tras el filtro de categoría, los puntos que queden son todos inicios, y la dirección de una línea la decide el inicio más cercano.
Dos extremos cuentan como el mismo punto solo si están bastante cerca. Un hueco detiene el recorrido. Los atributos no cambian. Solo se escribe el orden de vértices en el búfer de edición, y usted guarda la capa.</p>
<p>El chequeo solo reporta un tipo de error: una línea a la que ningún inicio llega. Que una línea simplemente termine es normal, no un error.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b> desde Dirección de líneas en la barra de la tabla.</li>
<li><b>Tolerancia de ajuste</b>, en metros, 0.6 por defecto (también cambiable en Ajustes → Parámetros). Si A está cerca de B y B cerca de C, los tres extremos son un punto, aunque A y C estén más lejos que la tolerancia. Tenga cuidado donde los extremos están muy juntos.</li>
<li><b>Capa de inicio</b>: una capa de puntos. El botón de la derecha filtra por categoría. Las categorías apagadas en la leyenda también se listan; márquelas para incluirlas. Los puntos que superen el filtro actúan todos como inicios a la vez. Un inicio que no toque ninguna línea se omite y se indica en el resultado.</li>
<li><b>Líneas</b>: añada al menos una capa de líneas. Puede añadir varias y filtrar cada una. A lo largo de una línea, el lado de inicio es el comienzo de la línea y el otro lado es el final.</li>
<li><b>Ramas</b>: cada extremo de línea es un nudo. Cuando el recorrido llega a un punto del que salen varias líneas, sigue cada una hacia fuera, alejándose de ese punto. Las ramas no son errores.</li>
<li><b>Finales</b>, opcionales, que solo cuentan donde las líneas forman un bucle: el bucle se corta en el final, como si las líneas no se unieran ahí, y ambos lados van hacia él. Donde no hay bucle no hace falta final y no cambia nada; el recorrido pasa por él. En un bucle sin final gana el inicio más cercano y la línea donde se encuentran ambos lados no tiene dirección: es un falso bucle, se escribe en una capa temporal y queda sin marcar. Exactamente un final, sobre un nudo, corta el bucle. Varios finales, o un final en medio de una línea y no en un nudo (seis líneas alrededor del inicio, cada una con un final en el medio), no eligen un corte único: esas líneas también van a una capa temporal y no se dan por correctas.</li>
<li><b>Después de Inicio</b>: la ventana de resultados queda encima y no tapa el mapa. Las líneas invertidas empiezan marcadas. Los falsos bucles no. Invertir marcadas solo da la vuelta a las marcadas. Una línea con un extremo abierto, una que nunca se conectó o una cuyas partes no coinciden se deja quieta.</li>
<li><b>Capas temporales</b>: marcan líneas invertidas, falsos bucles y direcciones sin decidir, visibles por defecto, para verlos en el mapa. Siguen ahí al cerrar la ventana de resultados. Quítelas usted si no las necesita.</li>
</ul>
""",
    ),
)
