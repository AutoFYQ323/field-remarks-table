# -*- coding: utf-8 -*-
"""German help. Five pages, same order as the Chinese and English help."""

PAGES = (
    (
        "Attributtabelle",
        """
<h3>Wozu sie dient</h3>
<p>Diese Tabelle steht neben der QGIS-Attributtabelle. Sie ersetzt F6 nicht und belegt dessen Kürzel nicht.
Ansehen und Bearbeiten eines Vektorlayers: sortieren, filtern, eine Spalte fixieren, Werte füllen, nach Kennung zurückkleben, exportieren.
Feldbemerkungen, Einstellungen, Feldzuordnungskopie und Linienrichtung haben je eine eigene Seite.</p>
<h3>Bedienung</h3>
<ul>
<li><b>Öffnen</b> über die Werkzeugleiste, <b>Vektor → Field Remarks Table</b> oder das Kontextmenü des Layers. Zuerst in der Layerliste einen Vektorlayer wählen.</li>
<li><b>Sprache</b> ist der Sprachknopf der Leiste. Der erste Start folgt der QGIS-Sprache, dann der Systemsprache; danach wird die Wahl gemerkt. Zur Auswahl stehen Chinesisch, Englisch, Spanisch, Französisch, Arabisch, Deutsch, Japanisch und Koreanisch; im Menü steht jede Sprache in ihrer eigenen Schreibweise. Bereits geöffnete Fenster wechseln sofort. Im Arabischen laufen Schaltflächen und Titel dieser Fenster von rechts nach links; Tabellenwerte bleiben links-nach-rechts.</li>
<li><b>Doppelklick auf die Zeilennummer</b> wählt das Objekt und zoomt hin.</li>
<li><b>Klick auf einen Spaltentitel</b> sortiert. Zahlartiger Text wird als Zahl sortiert.</li>
<li><b>Nach dem Sortieren</b> zeigt die Statusleiste für ZahlenSpalten den gefilterten und den vollen Gesamtwert. Andere Spalten prüfen auf Duplikate, ohne Groß-/Kleinschreibung.</li>
<li><b>Zellen aufziehen</b>: nach etwa einer halben Sekunde erscheinen an derselben Stelle Anzahl und Summe bei Zahlen, sonst die Duplikatprüfung.</li>
<li><b>Rechtsklick auf den Spaltentitel</b>: Spalte kopieren, mit Kopf kopieren, für Rückeinfügen kopieren, zurückeinfügen, eindeutige Werte, Duplikate auswählen, Leerwerte auswählen, Bemerkungen bearbeiten. Die Rückeinfügen-Kopie trägt die Kennung in Spalte 1 (Kopf beginnt mit #fid); nur Spalte 2 bearbeiten. Geschrieben wird nach Kennung, nicht nach Zeilenposition. Datumsangaben werden als 2024-09-01 kopiert.</li>
<li><b>Rechtsklick auf eine Zeilennummer</b>: angezeigte Zeilen wählen, z. B. 10-50, 1-20,35 oder 80- bis zur letzten Zeile.</li>
<li><b>Spalte ziehen</b> ändert nur die Reihenfolge in diesem Fenster. Die Feldreihenfolge des Layers bleibt. Nach dem Schließen wird nichts gemerkt.</li>
<li><b>Leiste oben, von links</b>: Anheften, Umfang, Fixieren, Kategorien-/Feldfilter, Textfilter. Eine blaue Pinnadel folgt dem aktuellen Layer der Legende, eine rote hält diese Tabelle fest. Umfang: alle Objekte, Auswahl, auf der Karte sichtbar (nach Verschieben/Zoomen nach ca. 500 ms aktualisiert) oder nur geänderte (in dieser Sitzung geändert oder neu, ungespeichert). Fixieren hält eine Spalte links und richtet die Zeilen aus. Der Filter hat zwei Listen: links Kategorie oder Feld, rechts Werte (ein Treffer genügt); das erste rechte Element „Alle“ fügt keinen Filter hinzu. Der Textfilter filtert beim Tippen nach etwa einer halben Sekunde. Beide Filter wirken zusammen.</li>
<li><b>Ungespeicherte Änderungen</b> zeigen eine hellgelbe Zelle. Beim Schließen erscheint kein zusätzlicher Hinweis. Speichern und Zurückrollen bleiben bei QGIS.</li>
<li><b>Wertprüfung</b> gilt für Handeingaben, Füllen, Schnelleingabe und Rückeinfügen. Was nicht ins Feld passt, wird übersprungen. Dezimalen in Ganzzahlern werden gerundet, zu langer Text wird vor dem Bestätigen aufgelistet. Ausdrucksfelder und nicht editierbare Verbindungen sind schreibgeschützt.</li>
<li><b>Füllen</b> (nur im Bearbeitungsmodus): Konstante, Nummerierung um Text, Text davor/danach, Ausdruck, Ersetzen. Aktualisiert gefilterte Zeilen oder die Auswahl. Eine Konstante kann ein anderer Feldname sein und kopiert dann diese Spalte. Text, der genau einem Feldnamen entspricht, in einfache Anführungszeichen setzen. Die Nummerierung setzt vor oder hinter den vorhandenen Text (eine Seite); der Text bleibt. Stellen: ohne Nullen, automatisch oder fest; führende Nullen bleiben nur auf Textfeldern. Leere Zellen bekommen nur die Nummer. Text davor/danach ändert nur vorhandenen Text. Der Ausdruck ist ein QGIS-Ausdruck. Ersetzen hat drei Arten und steht standardmäßig auf Standard plus Konstante. Standard ändert nur den Treffer, auch mehrfach in einer Zelle. Um den Treffer fügt davor oder danach ein und lässt den Text stehen. Ganzes Feld ersetzt die ganze Zelle, sobald sie trifft. Geschrieben wird eine Konstante oder ein Ausdruck je Objekt. Die drei Arten stehen in einem Feld. Groß/klein zählt, die Suche ist teilweise, außer Sie schalten das Symbol Ganze Zelle ein. Leere Zellen bleiben außen vor. Eine leere Konstante löscht den Treffer.</li>
<li><b>Gespeicherte Ausdrücke</b>: Steht Füllen auf Ausdruck, liegt rechts von ε ein Listensymbol. Damit fügen Sie gespeicherte Ausdrücke hinzu, bearbeiten, kommentieren, löschen und sortieren sie und öffnen einen im QGIS-Ausdrucksgenerator. Nach einer kurzen Pause listet das Tippen passende gespeicherte Ausdrücke. Der Pfeil rechts listet alle. Doppelklick markiert den ganzen Text, Ziehen markiert einen Teil. Das Feld bleibt ein Textfeld. Ein gewählter Eintrag erscheint als «Notiz» Ausdruck, etwa «Länge» $length oder «FYQ» round( $length / 1000, 2 ). Es läuft immer nur der Teil nach »: ändern Sie ihn im Feld auf round( $length / 1000, 4 ), läuft diese Fassung, die gespeicherte bleibt. Text, der nicht mit «…» beginnt, läuft wie eingegeben. Das Schreibfeld von Ersetzen hat dieselbe Liste, wenn es einen Ausdruck schreibt.</li>
<li><b>Standard-Füllmethode</b>: Unter Einstellungen → Parameter wählen Sie, womit die Füllleiste beginnt: Letzte merken (Standard; folgt jeder Änderung) oder immer Konstante, Nummerierung um Text, Text davor/danach, Ausdruck oder Ersetzen.</li>
<li><b>Alles auswählen / umkehren / Auswahl aufheben</b>: die ersten beiden beziehen sich auf die Zeilen dieser Tabelle. Aufheben leert die Layerauswahl.</li>
<li><b>Spaltenbreite</b>: „Anp“ verteilt die Spalten über das Fenster; „Voll“ passt sie dem Inhalt an und kann über das Fenster hinaus gehen. Manuell ziehen bleibt möglich.</li>
<li><b>Kopieren, Ausschneiden, Einfügen</b>: Strg+C kopiert die markierten Zellen. Das Leisten-Kopieren kopiert ganze Objekte. Zum Bearbeiten und Zurückkleben: „Spalte kopieren (Rundeinfahrt)“ am Spaltenkopf verwenden, die #fid-Spalte nicht ändern. Ohne passende Kennungen, bei Wiederholungen oder ganz leerer Wertspalte wird nichts geschrieben.</li>
<li><b>Export</b>: CSV kann rein numerischen Text als Zahl schreiben.</li>
<li><b>Feldverwaltung</b>: Felder anlegen, löschen, umbenennen. Hat das Feld im aktuellen Paket noch Anzeigenamen, Notizen oder Bedeutungen, fragt das Löschen, ob die Bemerkung mit entfernt wird.</li>
<li><b>Fenstertitel</b>: Layername - Koordinatensystem - Bearbeitungsstatus. Das System bevorzugt einen EPSG-Code. Der Status ist schreibgeschützt, in Bearbeitung, oder in Bearbeitung mit ungespeicherten Änderungen und deren Anzahl.</li>
<li><b>Statusleiste</b>: drei feste Anteile. Links 40 %: Gesamt, Angezeigt, Auswahl, Sortierung. Mitte 20 %: Linienlänge (Linienlayer, in Parameter eingeschaltet), aus der Geometrie berechnet, nie aus einem Feld. Rechts 40 %: Auswahlsumme oder Spaltenstatistik. Die drei Zahlen sind fett und schwarz. Weicht Angezeigt oder Auswahl von Gesamt ab, wird nur diese Zahl rot. Die Längenzahl und die Zahlen in der Doppelten-Zusammenfassung sind ebenfalls fett. Ein schmales Fenster zeigt in jedem Anteil nur, was hineinpasst.</li>
<li><b>Einstellungen</b>: das Zahnrad rechts außen. Drei Reiter: Werkzeugleiste, Tastenkürzel, Parameter. Alles wird auf diesem Rechner gemerkt.</li>
<li><b>Thema</b>: Standard, Kirschblütenrosa oder Minze. Alle Fenster dieses Plugins folgen; die Wahl wird lokal gemerkt.</li>
<li><b>Fenstergröße</b> bleibt nur während dieser QGIS-Sitzung erhalten.</li>
</ul>
""",
    ),
    (
        "Feldbemerkungen",
        """
<h3>Wozu sie dienen</h3>
<p>Feldbemerkungen sind das Kernstück. Ein Paket speichert wiederverwendbare Feldtexte: Anzeigenamen, Tooltip-Notizen, einfügbare Bedeutungen und Paketvariablen.
Pakete liegen auf diesem Rechner, geteilt über alle Projekte, nicht in einer .qgz. Layer und Felder werden über Namen zugeordnet, nicht über QGIS-Interne Kennungen.</p>
<p>Mit aktivem Paket zeigt der Kopf den Anzeigenamen über dem Feldnamen. Der Tooltip eines Spaltentitels zeigt Anzeigenamen, Notiz und Bedeutungen; solange vorhanden, fällt er nicht auf den nackten Feldnamen zurück.
Ohne aktives Paket bearbeitet diese Tabelle wie üblich und wendet nichts an. QGIS' eigene Attributtabelle (F6) bleibt unberührt.</p>
<p><b>Anzeige und Schreiben sind getrennt.</b> Anzeigenamen und Notizen sind nur für Menschen; sie landen nie in Objekten. Geschrieben wird die Konstante oder der Ausdruck einer Bedeutung.
Bei einer Wertzuordnung bleibt der gespeicherte Wert der ursprüngliche Code; hier wird nur der danebenstehende Text gepflegt.</p>
<h3>Bedienung</h3>
<ul>
<li><b>Erster Start</b>: Tabelle öffnen, Werkzeugleisten-Knopf Feldbemerkungen. Unter Pakete ein Paket anlegen und wählen. Die Liste des aktuellen Pakets öffnet sich in der Breite des Namens. Das Platzhalterpaket bleibt unberührt. Layer in der Legende wählen, links ein Feld anklicken, Anzeigenamen und Bedeutungen eintragen, dann Aktivieren.</li>
<li><b>Hilfe</b>: rechts neben dem aktuellen Paket öffnet Hilfe dieselbe Seite, die Feldbemerkungen aus der Hilfe der Werkzeugleiste.</li>
<li><b>Iconfarbe</b>: der Knopf öffnet nur das Fenster und ist kein Schalter. Farbe = ein echtes Paket ist gewählt und aktiviert. Grau = Platzhalter oder nicht aktiviert.</li>
<li><b>Platzhalterpaket</b>: jeder QGIS-Start beginnt bei „Standard (gesperrt)“. Es ist nicht editierbar, nicht aktivierbar, hat keine Variablen. Bis zum Beenden von QGIS bleibt das gewählte Paket gewählt; danach geht es wieder beim Platzhalter los. Das angelegte Paket bleibt erhalten — nur wieder wählen und aktivieren.</li>
<li><b>Pakete</b>: neu, löschen, umbenennen. Der Name muss eindeutig sein und darf nicht der Platzhaltername sein. Löschen entfernt nur die Konfiguration, keine Objekte.</li>
<li><b>Aktivieren</b> wendet das Paket an und prüft, ob Layer- und Feldnamen im Projekt existieren. Bei Abweichungen öffnet die Zuordnung, die alte Namen auf vorhandene lenkt. Öffnen, Paketwechsel und Vorschau lösen die Zuordnung nicht aus. Ein Paketwechsel deaktiviert erst; erneut aktivieren.</li>
<li><b>Bei Namensabweichungen</b> kann man das Paket unter neuem Namen kopieren und dann zuordnen; die Kopie verwirft fehlende Layer/Felder, das Original bleibt. Zuordnen geht auch ohne Kopie.</li>
<li><b>Felder pflegen</b>: die Liste ist der aktuelle Legendenlayer, letzter Eintrag ist der Layername. Ohne Aktivierung ist sie schreibgeschützt. Ein Feld hat Anzeigenamen, Notiz und Bedeutungen; der Layername nur Anzeigenamen und Notiz für den Legenden-Tooltip, ohne Bedeutungen und ohne Schreiben.</li>
<li><b>Bedeutungen</b>: eine Zeile ist eine Einfügeoption. Doppelklick bearbeitet die Beschreibung. Der Wert ist eine Konstante oder ein eingefügter QGIS-Ausdruck. Konstanten dürfen eine Variable enthalten, z. B. {{Stadt}}123. Ausdrücke gelten je Objekt; scheitert eines, wird es übersprungen, die anderen werden geschrieben. Die Einfügeliste zeigt nur Bedeutungen dieses Feldes; Variablen werden nicht automatisch überall eingeschüttet.</li>
<li><b>Wertzuordnung</b>: Felder mit QGIS-Wertzuordnung sind grün markiert. Diese Zeilen stammen aus QGIS, sind un löschbar. Der Text nach „war“ ist die Originalbeschreibung; „Standard wiederherstellen“ setzt sie zurück. Geändert wird nur der lesbare Text; die Zelle speichert weiterhin den Code. Auch in dieser Tabelle wählt der Auswahlkasten die Beschreibung, geschrieben wird der Code.</li>
<li><b>Wert-/Notizanzeige</b> ist der Leistenumschalter. Wert zeigt den gespeicherten Wert, Notiz die Bemerkungsbeschreibung, wenn vorhanden. Im Notizmodus durchsucht der Textfilter auch Beschreibungen. Der Umschalter ändert nur die Sicht, keine gespeicherten Werte.</li>
<li><b>Variablen</b> sitzen neben Aktivieren und gehören zum Paket, nicht zu ganz QGIS. Der Titel ist für Menschen, der Inhalt wird eingesetzt. Keine im Platzhalterpaket. Bei einer Bedeutung setzt „Variable einfügen“ {{Titel}} in den Wert, daneben geht fester Text. Ersetzt wird erst beim Einfügen. Spätere Variablenänderungen schreiben nichts zurück, und die Bedeutung muss nicht angepasst werden. Fehlt der Titel, meldet das Einfügen und schreibt kein Leeres.</li>
<li><b>Schnelleingabe</b> erscheint über der Tabelle, wenn Bemerkungen aktiv sind und der Layer editierbar ist. Die Ausklappboxen richten sich nach den Spalten. Nach Wahl einer Bedeutung: alles aktualisieren, gefilterte Zeilen, Auswahl oder abbrechen. Abbrechen behält die Wahl, damit die Füllen-Leiste sie schreiben kann. Konstanten schreiben den aufgelösten Text, Ausdrücke gelten je Objekt.</li>
<li><b>Zur Füllen-Leiste</b>: die Schnelleingabe nutzt vorhandene Bedeutungen. Die Füllen-Leiste schreibt auch Konstante, Nummerierung um Text, Text davor/danach, Ausdruck und Ersetzen ohne Bemerkungspaket. Beide brauchen den Bearbeitungsmodus; gespeichert wird über dieses Plugin oder QGIS.</li>
<li><b>Vorschau</b> zeigt lesend die Layer, Felder, Bedeutungen und Variablen des Pakets. Rot = im Projekt nicht gefunden. Standardmäßig nur Abweichungen.</li>
<li><b>Import/Export</b>: mehrere Pakete gleichzeitig; eine JSON kann mehrere samt Variablen tragen. Bei Namensgleichheit überschreiben oder umbenennen. Import aktiviert nichts; wählen und Aktivieren.</li>
<li><b>Aktualisieren</b>: hat ein anderes QGIS dieselbe Datei geändert, genügt ein Klick hier oder auf das Fenster. Kein Neustart nötig.</li>
<li><b>Beim Feldlöschen</b>: hat das Feld noch Anzeigenamen, Notizen oder Bedeutungen im aktuellen Paket, fragt die Feldverwaltung, ob die Bemerkung mitkommt. Bei Nein bleibt sie; ein späteres gleichnamiges Feld erhält sie wieder.</li>
</ul>
<h3>Empfehlung</h3>
<ul>
<li>Ein Paket pro Aufgabe, etwa eine Trasse oder ein Gebiet. Unzusammenhängende Layer erschweren die Zuordnung.</li>
<li>Anzeigenamen kurz, Regeln in die Notiz. Feste Wendungen in Bedeutungen, Auftragsabhängiges in Variablen.</li>
<li>Wertzuordnungen zuerst in QGIS anlegen; hier nur den lesbaren Text justieren.</li>
<li>Meldet die Leiste nach einem Projektwechsel Abweichungen, zuerst das richtige Paket prüfen; wer diese Konfiguration will, aktiviert und ordnet.</li>
</ul>
""",
    ),
    (
        "Einstellungen",
        """
<h3>Wozu sie dienen</h3>
<p>Einstellungen, das Zahnrad rechts außen, bündelt drei Dinge: welche Leistenknöpfe erscheinen und in welcher Reihenfolge, ein Tastenkürzel je Werkzeug und Laufzeitparameter. Alles bleibt nur auf diesem Rechner.</p>
<h3>Bedienung</h3>
<ul>
<li><b>Werkzeugleiste</b>: ziehen sortiert; Trennlinien ziehen mit. Abgewählte Knöpfe verschwinden, ihr Platz bleibt. „Trennlinie einfügen“ fügt nach der aktuellen Zeile, „Standard wiederherstellen“ stellt das Auslieferungsbild wieder her.</li>
<li><b>Tastenkürzel</b>: eine Zeile je Werkzeug. In das Feld klicken und die Kombination drücken; Rücktaste oder Entf löscht. Die Kürzel wirken nur innerhalb des QGIS-Fensters, nicht systemweit. Eine bereits von einer anderen Zeile, von festen In-Table-Tasten (Zellen kopieren, Ausschneiden, Einfügen) oder von einer anderen QGIS-Funktion belegte Kombination wird abgelehnt, und der Inhaber wird genannt. Bei geschlossener Tabelle öffnet der Druck im QGIS-Hauptfenster zuerst die Tabelle und führt dann das Werkzeug aus. „Alle löschen“ leert alles auf einmal.</li>
<li><b>Parameter</b>:
„Linienlänge der Auswahl zeigen“: bei Linienlayern zeigt die Mitte unten des Tabellenfensters die Gesamtlänge der gewählten Objekte. Aus der Geometrie berechnet, nie aus einem Feld. Standardmäßig aus.
„Filter folgt dem aktuellen Feld“: auf nicht kategorisierten Layern wechselt der Filter zur angeklickten Spalte (markierte Werte springen auf „Alle“); kategorisierte Layer bleiben beim Kategorienfilter. Standardmäßig ein.
„Wert-Obergrenze des Schnellfilters“: wie viele verschiedene Werte die Filterliste höchstens zeigt; bei mehr nur die ersten.
„Einrasttoleranz der Linienrichtungsprüfung (m)“: Enden zählen nur innerhalb dieser Distanz als verbunden, Standard 0.6. Das Toleranzfeld im Richtungsfenster folgt diesem Wert.
„Spaltenköpfe“: Nur Feldname (der Name in der Datenquelle), Alias zuerst (Alias oder Anzeigename aus der Feldbemerkung, falls vorhanden, sonst der Feldname) oder Alias und Feldname (zweizeilig, Standard).
„Standard-Füllmethode (Bearbeitungsmodus)“: Letzte merken (Standard) oder eine von Konstante, Nummerierung um Text, Text davor/danach, Ausdruck, Ersetzen.</li>
</ul>
""",
    ),
    (
        "Feldzuordnungskopie",
        """
<h3>Wozu sie dient</h3>
<p>Kopiert Objekte eines Vektorlayers in einen anderen und schreibt die Attribute nach der eingestellten Feldzuordnung.
Geometrietypen müssen passen. Quelle und Ziel dürfen nicht derselbe Layer sein. Abweichende Koordinatensysteme können umprojiziert werden.</p>
<h3>Bedienung</h3>
<ul>
<li><b>Öffnen</b> über die Feldzuordnungskopie in der Leiste. Das Fenster darf offen bleiben; Sprachwechsel übersetzt es sofort.</li>
<li><b>Layer</b>: oben Quelle, unten Ziel. Listen nach Punkt, Linie oder Polygon filtern. Die Quelle lässt sich aus einer Vektordatei laden oder mit „Aus Zwischenablage laden“: zuerst im Quellprojekt QGIS Bearbeiten → Objekte kopieren, dann den Knopf drücken, das Quell-KRS wählen — es entsteht ein temporärer Layer, der sofort Quelle ist.</li>
<li><b>Felder</b>: jede Zeile ist ein Zielfeld, rechts das Quellfeld. „Nach Namen zuordnen“ füllt eindeutige Paare. Die unscharfe Zuordnung ignoriert Leerzeichen und Unterstriche und füllt nur eindeutige Paare. „Zugeordnete Quellfelder ausblenden“ entfernt verbrauchte Quellfelder aus den übrigen Zeilen; aus erlaubt dasselbe Quellfeld mehrfach, Wiederholungen werden rot markiert.</li>
<li><b>Optionen</b>: nur die im Quell-Layer gewählten Objekte kopieren; bei abweichenden Koordinatensystemen ist die Umprojektion aufs Ziel standardmäßig an.</li>
<li><b>Jetzt kopieren</b> schreibt in den Bearbeitungspuffer des Ziels. Zum Speichern die Ziel-Layer-Bearbeitung abschließen.</li>
<li><b>Speichern</b> bewahrt die Zuordnung für dieses Layerpaar lokal auf.</li>
</ul>
""",
    ),
    (
        "Linienrichtung",
        """
<h3>Wozu sie dient</h3>
<p>Der Lauf geht gleichzeitig von jedem Punkt des Start-Layers nach außen, folgt verbundenen Linien, findet die in falscher Richtung digitalisierten und kann die Knotenreihenfolge umdrehen.
Es wird kein einzelner Start gewählt: Nach dem Kategorienfilter sind alle verbleibenden Punkte Starts, und die Richtung einer Linie bestimmt der nächstgelegene Start.
Endpunkte gelten nur bei ausreichender Nähe als gleich. Eine Lücke stoppt den Lauf. Attribute bleiben unberührt; nur die Knotenreihenfolge geht in den Bearbeitungspuffer, gespeichert wird selbst.</p>
<p>Die Prüfung meldet nur eine Fehlerart: eine Linie, die kein Start erreicht. Eine einfach endende Linie ist normal und kein Fehler.</p>
<h3>Bedienung</h3>
<ul>
<li><b>Öffnen</b> über die Linienrichtung in der Leiste.</li>
<li><b>Einrasttoleranz</b> in Metern, Standard 0.6 (auch unter Einstellungen → Parameter). Liegt A nahe B und B nahe C, sind alle drei Enden ein Punkt, selbst wenn A und C weiter als die Toleranz auseinanderliegen. Vorsicht bei dichten Endpunkten.</li>
<li><b>Start-Layer</b>: ein Punkt-Layer. Der Knopf rechts filtert nach Kategorie; auch in der Legende abgeschaltete Kategorien erscheinen und lassen sich anhaken. Jeder Punkt, der den Filter übersteht, wirkt gleichzeitig als Start. Ein Start ohne Linienkontakt wird übersprungen und im Ergebnis genannt.</li>
<li><b>Linien</b>: mindestens ein Linien-Layer, mehrere möglich, jede mit eigenem Kategorienfilter. Entlang einer Linie ist die Startseite der Linienanfang, die andere das Linienende.</li>
<li><b>Verzweigungen</b>: Jedes Linienende ist ein Knoten. Erreicht der Lauf einen Punkt, von dem mehrere Linien abgehen, wird jede nach außen verfolgt, weg von diesem Punkt. Verzweigungen sind keine Fehler.</li>
<li><b>Enden</b> sind optional und wirken nur, wo Linien eine Schleife bilden: Die Schleife wird am Ende getrennt, als wären die Linien dort nicht verbunden, und beide Seiten laufen darauf zu. Ohne Schleife braucht es kein Ende und es ändert nichts; der Lauf geht hindurch. Auf einer Schleife ohne Ende gewinnt der nähere Start, und die Linie, an der sich beide Seiten treffen, hat keine Richtung: eine falsche Schleife, in einen temporären Layer geschrieben und in der Tabelle nicht angehakt. Genau ein Ende auf einem Knoten trennt die Schleife. Mehrere Enden, oder ein Ende mitten auf einer Linie statt auf einem Knoten (sechs Linien um den Start, jede mit einem Ende in der Mitte), ergeben keine eindeutige Trennung: diese Linien werden ebenfalls in einen temporären Layer geschrieben und nicht als richtig behandelt.</li>
<li><b>Nach dem Start</b>: das Ergebnisfenster bleibt oben und verdeckt die Karte nicht. Verkehrte Linien starten angehakt, falsche Schleifen nicht. „Aktivierte umdrehen“ dreht nur Angehakte. Linien mit offenem Ende, nie erreichte oder widersprüchliche bleiben liegen.</li>
<li><b>Temporäre Layer</b> markieren verkehrte Linien, falsche Schleifen und unklare Richtungen, standardmäßig sichtbar, für die Karte. Sie überleben das Fenster und lassen sich bei Bedarf selbst entfernen.</li>
</ul>
""",
    ),
)
