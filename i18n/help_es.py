# -*- coding: utf-8 -*-
"""Spanish help. Five pages, same order as the Chinese and English help."""

PAGES = (
    (
        "Tabla de atributos",
        """
<h3>Qué hace</h3>
<p>Es una tabla junto a la tabla de atributos de QGIS. No sustituye F6 ni usa su atajo.
Sirve para ver y editar una capa vectorial: ordenar, filtrar, fijar una columna, rellenar valores, pegar por identificador y exportar.
Las notas de campos, la nomenclatura rápida, la copia de campos y la dirección de líneas tienen cada una su página.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b>: botón de la barra, <b>Vectorial → Field Remarks Table</b>, o el menú contextual de la capa. Primero seleccione una capa vectorial en el panel de capas.</li>
<li><b>Idioma</b>: botón de idioma de la barra. La primera vez sigue el idioma de QGIS y, si no hay, el del sistema; después se recuerda la elección. Hay chino, inglés, español, francés y árabe. Al cambiar, las ventanas ya abiertas de este complemento pasan a ese idioma. En árabe, los botones y títulos van de derecha a izquierda. Los valores de la tabla siguen de izquierda a derecha.</li>
<li><b>Doble clic en el número de fila</b>: selecciona el elemento y acerca el mapa.</li>
<li><b>Clic en el título de columna</b>: ordena. El texto que parece un número se ordena como número.</li>
<li><b>Después de ordenar</b>, la barra de estado muestra el total filtrado y el total completo de las columnas numéricas. Las demás buscan duplicados, sin distinguir mayúsculas.</li>
<li><b>Seleccionar celdas</b>. Al cabo de medio segundo, el mismo sitio muestra cantidad y suma si son números, o duplicados en otro caso.</li>
<li><b>Clic derecho en el título</b>: copiar la columna, copiar con encabezado, copiar para devolver, pegar en la columna, valores únicos, seleccionar duplicados, seleccionar vacíos o editar notas. La copia para devolver lleva el identificador en la columna 1 (el encabezado empieza por #fid). Solo se edita la columna 2. Se escribe por identificador, no por posición. Las fechas se copian como 2024-09-01.</li>
<li><b>Clic derecho en el número de fila</b>: selecciona filas visibles, por ejemplo 10-50, 1-20,35 o 80- hasta la última.</li>
<li><b>Arrastrar una columna</b> solo cambia el orden en esta ventana. El orden de campos de la capa no cambia. Al cerrar no se recuerda.</li>
<li><b>Barra superior, de izquierda a derecha</b>: fijar, ámbito, congelar, filtro de categoría o campo, filtro de texto. El texto azul sigue la capa actual de la leyenda. El rojo mantiene esta capa. El ámbito puede ser todos los elementos, la selección, lo visible en el mapa o lo modificado en esta edición. Congelar deja una columna a la izquierda y alinea las filas. El filtro tiene dos listas: categoría o campo a la izquierda, y valores a la derecha (basta uno marcado). El primer valor de la derecha, Todos, no añade filtro. El texto filtra al escribir, tras medio segundo. Los dos filtros actúan a la vez.</li>
<li><b>Cambios sin guardar</b>: la celda queda en amarillo claro. Cerrar la ventana no pregunta otra vez. Guardar y deshacer siguen en QGIS.</li>
<li><b>Comprobación al escribir</b>: edición manual, relleno, inserción rápida y pegado se comprueban según el tipo de campo. Lo que no cabe se omite. Un decimal en un entero se redondea. Un texto demasiado largo se lista antes de confirmar. Los campos de expresión y las uniones no editables son de solo lectura.</li>
<li><b>Relleno</b> (solo en edición): constante, número alrededor del texto, texto añadido, expresión y reemplazo. Puede actualizar las filas filtradas o la selección. Una constante puede ser el nombre de otro campo, y entonces se copia esa columna. Para escribir un texto igual al nombre de un campo, póngalo entre comillas simples. El número alrededor del texto se pone delante o detrás y conserva el texto. El ancho puede ser sin ceros, automático o fijo. Los ceros solo se guardan en campos de texto. Una celda vacía recibe solo el número. El texto añadido solo cambia lo que ya tiene texto. La expresión es una expresión de QGIS. El reemplazo es literal y cambia todas las coincidencias de la celda.</li>
<li><b>Seleccionar todo / invertir / quitar selección</b>: las dos primeras actúan sobre las filas de esta tabla. Quitar selección vacía la selección de la capa.</li>
<li><b>Ancho de columna</b>: Ajustar reparte las columnas en la ventana. Completo las abre según el contenido y puede pasar el borde. Aún se puede arrastrar.</li>
<li><b>Copiar, cortar, pegar</b>: Ctrl+C copia las celdas seleccionadas. Copiar de la barra copia elementos enteros. Para editar y devolver: Copiar columna (ida y vuelta). No cambie la columna #fid. Si los identificadores no coinciden, se repiten o la columna de valores está vacía, no se escribe nada.</li>
<li><b>Exportar</b>: CSV puede escribir el texto numérico como número. KMZ puede exportar solo las filas de esta tabla y usar colores de símbolo único, categorizado o graduado. Los símbolos por reglas no se colorean. Si la coordenada no se transforma, se avisa.</li>
<li><b>Gestión de campos</b>: crear, borrar y renombrar. Si el paquete actual aún tiene nombre o significados para ese campo, al borrarlo pregunta si también se borra la nota.</li>
<li><b>Orden de la barra</b>: el botón de la derecha. Se pueden ocultar botones y arrastrar el orden. Se recuerda en este equipo. La nomenclatura rápida no sale en la barra hasta que se marque aquí.</li>
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
<li><b>La primera vez</b>: abra la tabla y pulse Notas de campos. En Paquetes, cree uno y selecciónelo. El paquete de reserva no se puede editar. Elija la capa en la leyenda, pulse un campo a la izquierda, escriba el nombre y los significados, y pulse Activar.</li>
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
        "Nomenclatura rápida",
        """
<h3>Qué hace</h3>
<p>Escribe en los elementos seleccionados los valores de campo sacados de una simbología por categorías o por reglas. No depende de que las notas de campos estén activas.
Se listan todas las clases, estén o no marcadas en la leyenda. Puntos, líneas y polígonos tienen que ser del mismo tipo de geometría.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b>: en la tabla, abra el orden de la barra y marque Mostrar nomenclatura rápida. Aparece un botón verde. La elección se recuerda en este equipo y, por defecto, está apagada.</li>
<li><b>Lista</b>: cada fila es una clase. El número entre paréntesis lo lleva esta ventana. Se cuenta al abrir o cambiar de capa, y luego se ajusta con lo que acaba de escribir. El total junto al nombre de la capa es la suma de las clases, para compararlo con la leyenda de QGIS.</li>
<li><b>Pulsar una clase</b>: pide confirmación, salvo que marque la casilla de escribir al momento.</li>
<li><b>Fijar la capa</b> está apagado por defecto. Tras fijar la capa categorizada A, seleccionar elementos en A y pulsar una clase solo cambia atributos. Seleccionar en otra capa y pulsar una clase copia la geometría a A y luego aplica esa clase. La capa de origen no cambia, y A no gana los campos de origen.</li>
<li><b>Autoguardado</b> está apagado por defecto, así que aún se puede deshacer. Los conteos de la leyenda cambian cuando guarda en QGIS. «Guardar pasados N segundos» escribe primero y luego lanza Guardar ediciones de la capa una vez, tras unos N segundos. Otros clics reinician ese tiempo y se guarda una sola vez. Al cerrar la ventana se guarda enseguida. Ese guardado escribe todos los cambios sin guardar de la capa y no se puede deshacer.</li>
<li><b>Actualizar conteos de la leyenda</b> solo corre cuando se pulsa. Vuelve a poner el renderizador actual en la capa para que QGIS recalcule. No cambia elementos y no se ejecuta solo.</li>
<li><b>Si una clase no se puede escribir</b>, por ejemplo un renderizador graduado o una regla sin valor de campo, el clic explica por qué y no escribe nada.</li>
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
<li><b>Capas</b>: origen en la primera fila, destino en la segunda. Filtre las listas por punto, línea o polígono. El origen también puede cargarse desde un archivo vectorial que QGIS abra.</li>
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
<p>Parte de un punto que usted elige, recorre las líneas conectadas, encuentra las que están digitalizadas al revés y les da la vuelta al orden de vértices.
Dos extremos cuentan como el mismo punto solo si están bastante cerca. Un hueco detiene el recorrido. Los atributos no cambian. Solo se escribe el orden de vértices en el búfer de edición, y usted guarda la capa.</p>
<h3>Cómo se usa</h3>
<ul>
<li><b>Abrir</b> desde Dirección de líneas en la barra de la tabla.</li>
<li><b>Tolerancia de ajuste</b>, en metros. Si A está cerca de B y B cerca de C, los tres extremos son un punto, aunque A y C estén más lejos que la tolerancia. Tenga cuidado donde los extremos están muy juntos.</li>
<li><b>Capa de inicio</b>: una capa de puntos. El botón de la derecha filtra por categoría. Las categorías apagadas en la leyenda también se listan. Márquelas para incluirlas. Todos significa todos los puntos de esa capa.</li>
<li><b>Líneas</b>: añada al menos una capa de líneas. Puede añadir varias y filtrar cada una. A lo largo de una línea, el lado de inicio es el comienzo de la línea y el otro lado es el final.</li>
<li><b>Finales</b>, opcionales. El recorrido se detiene en un final. Si no hay finales, una línea no se trata como falso bucle solo porque, al quitarla, un lado quede inalcanzable desde el inicio.</li>
<li><b>Elija un inicio</b> en la lista. Busque por nombre o por identificador. Inicio sigue desactivado hasta que haya un punto elegido.</li>
<li><b>Después de Inicio</b>: la ventana de resultados queda encima y no tapa el mapa. Las líneas invertidas empiezan marcadas. Los falsos bucles no. Invertir marcadas solo da la vuelta a las marcadas. Una línea con un extremo abierto, una que nunca se conectó o una cuyas partes no coinciden se deja quieta.</li>
<li><b>Capas temporales</b>: marcan inicios, finales o problemas de dirección para verlos en el mapa. Siguen ahí al cerrar la ventana de resultados. Quítelas usted si no las necesita.</li>
</ul>
""",
    ),
)
