# -*- coding: utf-8 -*-
"""French help. Five pages, same order as the Chinese and English help."""

PAGES = (
    (
        "Table attributaire",
        """
<h3>Rôle</h3>
<p>C'est une table à côté de la table attributaire de QGIS. Elle ne remplace pas F6 et n'utilise pas son raccourci.
Elle sert à voir et modifier une couche vecteur : trier, filtrer, figer une colonne, remplir des valeurs, coller par identifiant et exporter.
Les remarques de champs, les réglages, la copie de champs et le sens des lignes ont chacun leur page.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> : bouton de la barre, <b>Vecteur → Field Remarks Table</b>, ou le menu contextuel de la couche. Sélectionnez d'abord une couche vecteur dans le panneau des couches.</li>
<li><b>Langue</b> : bouton de langue de la barre. Le premier lancement suit la langue de QGIS, puis celle du système, et le choix est mémorisé. Les choix sont le chinois, l'anglais, l'espagnol, le français, l'arabe, l'allemand, le japonais et le coréen ; chaque langue s'affiche avec son propre nom dans le menu. Les fenêtres déjà ouvertes de ce module passent tout de suite à la langue choisie. En arabe, les boutons et les titres vont de droite à gauche. Les valeurs du tableau restent de gauche à droite.</li>
<li><b>Double-clic sur le numéro de ligne</b> : sélectionne l'entité et zoome dessus.</li>
<li><b>Clic sur l'en-tête</b> : trie. Un texte qui ressemble à un nombre est trié comme un nombre.</li>
<li><b>Après un tri</b>, la barre d'état montre le total filtré et le total complet des colonnes numériques. Les autres signalent les doublons, sans tenir compte de la casse.</li>
<li><b>Sélection de cellules</b>. Au bout d'une demi-seconde, le même endroit montre le nombre et la somme s'il s'agit de nombres, sinon les doublons.</li>
<li><b>Clic droit sur l'en-tête</b> : copier la colonne, copier avec l'en-tête, copier pour recoller, recoller, valeurs uniques, sélectionner les doublons, sélectionner les vides, ou modifier les remarques. La copie aller-retour met l'identifiant en colonne 1 (l'en-tête commence par #fid). On ne modifie que la colonne 2. L'écriture se fait par identifiant, pas par position. Les dates sont copiées comme 2024-09-01.</li>
<li><b>Clic droit sur le numéro de ligne</b> : sélectionne les lignes affichées, par exemple 10-50, 1-20,35 ou 80- jusqu'à la dernière.</li>
<li><b>Glisser une colonne</b> ne change l'ordre que dans cette fenêtre. L'ordre des champs de la couche ne change pas. Il n'est pas gardé à la fermeture.</li>
<li><b>Barre du haut, de gauche à droite</b> : épingler, emprise, figer, filtre de catégorie ou de champ, filtre de texte. L'épingle bleue suit la couche actuelle de la légende. L'épingle rouge garde cette couche. L'emprise peut être toutes les entités, la sélection, le visible sur la carte, ou le modifié dans cette session. Figer garde une colonne à gauche et aligne les lignes. Le filtre a deux listes : catégorie ou champ à gauche, valeurs à droite (une valeur cochée suffit). Le premier élément de droite, Tous, n'ajoute pas de filtre. Le texte filtre à la frappe, après une demi-seconde. Les deux filtres agissent ensemble.</li>
<li><b>Modifications non enregistrées</b> : la cellule devient jaune pâle. Fermer la fenêtre ne pose pas une autre question. Enregistrer et annuler restent dans QGIS.</li>
<li><b>Contrôle à l'écriture</b> : saisie, remplissage, insertion rapide et collage sont vérifiés selon le type du champ. Ce qui ne tient pas est ignoré. Une décimale écrite dans un entier est arrondie. Un texte trop long est listé avant confirmation. Les champs d'expression et les jointures non modifiables sont en lecture seule.</li>
<li><b>Remplissage</b> (édition seulement) : constante, numéro autour du texte, texte ajouté, expression et remplacement. On peut mettre à jour les lignes filtrées ou la sélection. Une constante peut être le nom d'un autre champ : cette colonne est alors copiée. Pour écrire un texte exactement égal à un nom de champ, mettez-le entre apostrophes. Le numéro autour du texte se place avant ou après et garde le texte. La largeur peut être sans zéros, automatique ou fixe. Les zéros ne restent que dans les champs texte. Une cellule vide ne reçoit que le numéro. Le texte ajouté ne change que le texte déjà présent. L'expression est une expression QGIS. Le remplacement a trois modes ; par défaut, standard plus une constante. Standard ne change que le texte trouvé, partout dans la cellule. Autour de la recherche insère avant ou après et garde l'original. Champ entier remplace toute la cellule dès qu'elle correspond. On peut écrire une constante ou une expression par entité. Les trois modes sont dans une seule case. La casse compte et la recherche est partielle, sauf si vous allumez l'icône de correspondance entière. Les cellules vides sont ignorées. Une constante vide efface le texte trouvé.</li>
<li><b>Expressions enregistrées</b> : avec Remplissage sur Expression, une icône de liste apparaît à droite de ε. Il permet d'ajouter, modifier, annoter, supprimer et ordonner des expressions enregistrées, et d'en ouvrir une dans le constructeur d'expression QGIS. Après une courte pause, la saisie liste les expressions enregistrées qui correspondent. La flèche à droite les liste toutes. Un double-clic sélectionne tout le texte, un glisser en sélectionne une partie. La case reste une zone de texte. Un élément choisi s'affiche comme «note» expression, par exemple «Longueur» $length ou «FYQ» round( $length / 1000, 2 ). Seule la partie après » s'exécute : changez-la en round( $length / 1000, 4 ) dans la case et c'est elle qui s'exécute, l'enregistrée ne change pas. Un texte qui ne commence pas par «…» s'exécute tel quel. La case d'écriture de Remplacer a la même liste quand elle écrit une expression.</li>
<li><b>Méthode de remplissage par défaut</b> : dans Réglages → Paramètres, choisissez la méthode de départ de la barre de remplissage : Retenir le dernier (par défaut ; suit chaque changement), ou toujours Constante, Numéro autour du texte, Ajouter du texte, Expression ou Remplacer.</li>
<li><b>Tout sélectionner / inverser / effacer</b> : les deux premières agissent sur les lignes de cette table. Effacer vide la sélection de la couche.</li>
<li><b>Largeur de colonne</b> : Ajuster répartit les colonnes dans la fenêtre. Complet les ouvre selon le contenu et peut dépasser la fenêtre. On peut encore tirer une largeur.</li>
<li><b>Copier, couper, coller</b> : Ctrl+C copie les cellules choisies. Copier de la barre copie des entités entières. Pour modifier puis recoller : Copier la colonne (aller-retour). Ne changez pas la colonne #fid. Si les identifiants ne correspondent pas, se répètent, ou si la colonne de valeurs est vide, rien n'est écrit.</li>
<li><b>Exporter</b> : le CSV peut écrire un texte numérique comme un nombre.</li>
<li><b>Gestion des champs</b> : créer, supprimer et renommer. Si le paquet actuel a encore un nom ou des significations pour ce champ, la suppression demande s'il faut aussi supprimer la remarque.</li>
<li><b>Titre de la fenêtre</b> : nom de la couche - système de coordonnées - état d'édition. Le système préfère un code EPSG. L'état est lecture seule, en édition, ou en édition avec des changements non enregistrés et leur nombre.</li>
<li><b>Barre d'état</b> : trois parts fixes. Les 40 % de gauche : total, affichées, sélectionnées, tri. Les 20 % du milieu : longueur de ligne (couche de lignes, après activation dans Paramètres), calculée depuis la géométrie, jamais depuis un champ. Les 40 % de droite : total de la sélection ou statistiques de colonne. Les trois nombres sont en gras et en noir. Si les affichées ou les sélectionnées diffèrent du total, seul ce nombre passe au rouge. Le nombre de la longueur et les nombres du résumé des doublons sont aussi en gras. Une fenêtre étroite n'affiche que ce qui tient dans chaque part.</li>
<li><b>Réglages</b> : l'engrenage tout à droite. Trois onglets : Barre d'outils, Raccourcis et Paramètres. Tout est mémorisé sur cet ordinateur.</li>
<li><b>Thème</b> : défaut, rose sakura ou menthe. Toutes les fenêtres de ce module le suivent. Le choix est mémorisé sur cet ordinateur.</li>
<li><b>Taille de la fenêtre</b> : mémorisée tant que cette session QGIS est ouverte.</li>
</ul>
""",
    ),
    (
        "Remarques de champs",
        """
<h3>Rôle</h3>
<p>Les remarques de champs sont la fonction principale. Un paquet garde, pour des couches vecteur, un nom affiché, une note au survol, des significations à insérer et des variables de paquet.
Les paquets sont enregistrés sur cet ordinateur et partagés par tous les projets. Ils ne sont pas dans un fichier .qgz. Les couches et les champs sont reliés par leur nom, pas par l'identifiant interne de QGIS.</p>
<p>Quand le paquet est activé, l'en-tête montre le nom affiché au-dessus du nom du champ. Le survol montre le nom, la note et les significations. Tant que ces textes existent, le survol ne retombe pas sur le seul nom de champ.
Quand le paquet est arrêté, la table s'édite comme d'habitude et n'applique pas cette configuration. La table de QGIS (F6) n'est pas modifiée.</p>
<p><b>Afficher et écrire sont deux choses.</b> Le nom affiché et la note sont seulement lus. Ils ne sont pas écrits dans l'entité. Ce qui est écrit, c'est la constante ou l'expression de la signification.
Sur un champ à table de valeurs, la valeur stockée reste le code. Ici on modifie le texte affiché à côté.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>La première fois</b> : ouvrez la table et cliquez sur Remarques de champs. Dans Paquets, créez-en un et sélectionnez-le. La liste du paquet actuel s'ouvre à la largeur du nom. Le paquet de réserve ne se modifie pas. Choisissez la couche dans la légende, cliquez un champ à gauche, remplissez le nom et les significations, puis cliquez sur Activer.</li>
<li><b>Aide</b> : à droite du paquet actuel, Aide ouvre cette même page, celle des remarques de champs dans l'aide de la barre.</li>
<li><b>Couleur de l'icône</b> : le bouton ouvre seulement la fenêtre. Ce n'est pas l'interrupteur. En couleur, un vrai paquet est choisi et activé. En gris, c'est le paquet de réserve, ou l'activation est arrêtée.</li>
<li><b>Paquet de réserve</b> : chaque ouverture de QGIS commence sur Défaut (verrouillé). Il ne se modifie pas, ne s'active pas et n'a pas de variables. Tant que QGIS reste ouvert, le paquet choisi est mémorisé. À la fermeture, on revient au paquet de réserve. Le paquet construit est toujours là : sélectionnez-le et activez-le à nouveau.</li>
<li><b>Paquets</b> : nouveau, supprimer et renommer. Le nom doit être unique et ne peut pas être celui du paquet de réserve. Supprimer un paquet supprime cette configuration. Les entités de la couche ne changent pas.</li>
<li><b>Activer</b> applique le paquet aux champs et vérifie que les noms de couche et de champ existent dans ce projet. S'ils ne correspondent pas, l'appariement s'ouvre pour désigner le nom actuel. Ouvrir la fenêtre, changer de paquet ou afficher l'aperçu n'ouvre pas l'appariement. Changer de paquet désactive : il faut activer de nouveau.</li>
<li><b>Si les noms ne correspondent pas</b> : on peut copier vers un nouveau paquet, puis apparier. La copie abandonne les couches et champs absents de ce projet. Le paquet d'origine ne bouge pas. On peut aussi apparier sans copier.</li>
<li><b>Modifier les champs</b> : la liste est la couche actuelle de la légende. Le dernier élément est le nom de la couche. Tant que le paquet n'est pas activé, la liste est en lecture seule. Un champ a un nom affiché, une note et des significations. Le nom de couche n'a qu'un nom affiché et une note pour la légende. Il n'a pas de significations et n'est pas écrit dans les attributs.</li>
<li><b>Significations</b> : une ligne est un choix d'insertion. Double-cliquez pour modifier la description. La valeur peut être une constante ou une expression QGIS collée. Une constante peut contenir une variable, par exemple {{ville}}123. L'expression est calculée pour chaque entité. Une entité en échec est ignorée, les autres sont écrites. La liste ne montre que les significations de ce champ. Les variables ne sont pas versées seules dans chaque colonne.</li>
<li><b>Table de valeurs</b> : un champ qui a déjà une table de valeurs QGIS est marqué en vert. Ces lignes viennent de QGIS et ne se suppriment pas. Le texte après « était » est la description d'origine. Restaurer le défaut remet cette description. On modifie le texte lu par les gens. La cellule garde le code. Dans cette table, on peut aussi choisir la description dans une liste. La valeur écrite reste le code.</li>
<li><b>Valeur / note</b> est le bouton de la barre. Valeur montre ce qui est stocké. Note montre la description lorsqu'elle existe. En mode note, le filtre de texte cherche aussi les descriptions. Le bouton change ce qui est vu, pas ce qui est déjà stocké.</li>
<li><b>Variables</b> : à côté d'Activer. Elles appartiennent à ce paquet, pas à tout QGIS. Le titre est ce qu'on lit. Le contenu est le texte substitué. Le paquet de réserve n'en a pas. En ajoutant une signification, Insérer une variable place {{titre}} dans la valeur. On peut ajouter du texte fixe à côté. La substitution a lieu au moment de l'insertion. Changer la variable plus tard ne réécrit pas les valeurs déjà stockées, et il n'est pas nécessaire de modifier la signification. Si le titre manque, un message l'indique et rien de vide n'est écrit.</li>
<li><b>Insertion rapide</b> : elle apparaît au-dessus de la table quand les remarques sont activées et que la couche est en édition. Les listes s'alignent sur les colonnes. Après un choix : tout mettre à jour, les lignes filtrées, la sélection, ou annuler. Annuler garde le choix pour l'écrire avec la barre de remplissage. Une constante écrit le texte déjà résolu. Une expression est calculée par entité.</li>
<li><b>Barre de remplissage</b> : l'insertion rapide utilise des significations déjà préparées. La barre peut aussi écrire une constante, un numéro autour du texte, du texte ajouté, une expression ou un remplacement sans paquet de remarques. Les deux demandent le mode édition. Enregistrez depuis ce module ou depuis QGIS pour que le fichier reçoive la modification.</li>
<li><b>Aperçu</b> : lecture seule des couches, champs, significations et variables de ce paquet. En rouge, ce qui ne correspond pas à ce projet. Par défaut, seules les différences sont listées.</li>
<li><b>Importer / Exporter</b> : plusieurs paquets peuvent être cochés. Un JSON peut en contenir plusieurs, variables comprises. En cas de même nom, on choisit d'écraser ou de renommer. L'import n'active pas le paquet. Sélectionnez-le et cliquez sur Activer.</li>
<li><b>Actualiser</b> : si une autre fenêtre QGIS a modifié les mêmes paquets, cliquez sur Actualiser ou sur cette fenêtre. Pas besoin de redémarrer.</li>
<li><b>Suppression d'un champ</b> : si Gestion des champs supprime un champ qui a encore un nom, une note ou des significations dans le paquet, elle demande s'il faut aussi supprimer la remarque. Si on la garde, elle reste dans le paquet. Un champ ultérieur du même nom sur cette couche la reçoit encore.</li>
</ul>
<h3>Une mise en place pratique</h3>
<ul>
<li>Un paquet par travail, par exemple un tracé ou un secteur. Des couches sans rapport dans le même paquet rendent l'appariement difficile à lire.</li>
<li>Nom affiché court, règle dans la note. Le texte fixe répété va dans les significations. Les noms et numéros qui changent selon le travail vont dans les variables.</li>
<li>Réglez d'abord dans QGIS les codes et les descriptions de la table de valeurs. Ici, on n'ajuste que la description lue par les gens.</li>
<li>Après avoir ouvert un autre projet, si la ligne d'état dit que des couches ou des champs ne correspondent pas, vérifiez le paquet choisi. S'il est le bon, cliquez sur Activer et appariez les noms.</li>
</ul>
""",
    ),
    (
        "Réglages",
        """
<h3>À quoi ça sert</h3>
<p>Réglages, l'engrenage à l'extrémité droite de la barre, rassemble trois choses : quels boutons s'affichent et dans quel ordre, un raccourci clavier par outil, et les paramètres d'exécution. Tout reste stocké sur cet ordinateur uniquement.</p>
<h3>Comment l'utiliser</h3>
<ul>
<li><b>Barre d'outils</b> : glissez pour réordonner ; les séparateurs se glissent aussi. Décocher un bouton le masque et garde sa place. Insérer un séparateur en ajoute un après la ligne courante. Restaurer le défaut remet la disposition d'origine.</li>
<li><b>Raccourcis</b> : une ligne par outil. Cliquez dans la case et pressez une combinaison pour l'enregistrer ; Retour arrière ou Suppr l'efface. Ils ne répondent que dans la fenêtre QGIS, pas partout dans le système. Une combinaison déjà prise par une autre ligne, par une touche fixe de la table (copier des cellules, couper, coller) ou par une autre fonction QGIS est refusée, et son détenteur est nommé. Table fermée, presser le raccourci dans la fenêtre principale de QGIS ouvre d'abord la table, puis lance l'outil. Tout effacer vide tous les enregistrements d'un coup.</li>
<li><b>Paramètres</b> :
« Afficher la longueur de ligne des entités sélectionnées » : pour les couches de lignes, le centre du bas de la fenêtre du tableau montre la longueur totale des entités sélectionnées. Calculée depuis la géométrie, jamais depuis un champ. Désactivé par défaut.
« Le filtre suit le champ actif » : sur les couches non catégorisées, le filtre suit la colonne cliquée (les valeurs cochées reviennent à Tout) ; les couches catégorisées restent sur le filtre par catégorie. Activé par défaut.
« Limite de valeurs du filtre rapide » : combien de valeurs distinctes la boîte Filtrer peut lister au maximum. Au-delà, seules les premières s'affichent.
« Tolérance d'accrochage du contrôle de direction (m) » : deux extrémités ne comptent comme reliées que sous cette distance. Défaut 0.6. La case de tolérance de la fenêtre de direction suit cette valeur.
« En-têtes de colonne » : Nom de champ seul (le nom de la source de données), Alias d'abord (l'alias ou le nom affiché de la remarque de champ s'il existe, sinon le nom du champ) ou Alias et nom de champ (deux lignes, par défaut).
« Méthode de remplissage par défaut (édition) » : Retenir le dernier (par défaut), ou l'une de Constante, Numéro autour du texte, Ajouter du texte, Expression, Remplacer.</li>
</ul>
""",
    ),
    (
        "Copie de champs",
        """
<h3>Rôle</h3>
<p>Copie des entités d'une couche vecteur vers une autre et écrit les attributs avec la correspondance de champs que vous réglez.
Les types de géométrie doivent correspondre. La source et la cible ne peuvent pas être la même couche. Des systèmes de coordonnées différents peuvent être reprojetés.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> depuis Copie de champs sur la barre de la table. La fenêtre peut rester ouverte. Changer de langue met ses libellés à jour tout de suite.</li>
<li><b>Couches</b> : source sur la première ligne, cible sur la seconde. Filtrez les listes par point, ligne ou polygone. La source peut être chargée depuis un fichier vecteur que QGIS sait ouvrir, ou avec « Charger depuis le presse-papiers » : utilisez d'abord Édition → Copier des entités de QGIS dans le projet source, puis cliquez sur le bouton, choisissez le SCR source, et une couche temporaire est créée et devient la source.</li>
<li><b>Champs</b> : chaque ligne est un champ cible. Choisissez le champ source à droite. Apparier les noms identiques remplit les paires uniques. L'appariement approximatif ignore espaces et traits de soulignement, et ne remplit une paire que si elle est unique. Masquer les champs source déjà utilisés les retire des autres listes. Décochez pour envoyer un même champ source vers plusieurs cibles. Les répétitions sont marquées en rouge.</li>
<li><b>Options</b> : ne copier que les entités sélectionnées sur la source. Quand les systèmes de coordonnées diffèrent, la reprojection vers la cible est activée par défaut.</li>
<li><b>Copier maintenant</b> écrit dans le tampon d'édition de la cible. Enregistrez les modifications de la cible pour les garder dans le fichier.</li>
<li><b>Enregistrer</b> garde la correspondance sur cet ordinateur pour la prochaine ouverture de cette paire de couches.</li>
</ul>
""",
    ),
    (
        "Sens des lignes",
        """
<h3>Rôle</h3>
<p>Le parcours part en même temps de tous les points de la couche de départ, suit les lignes connectées, repère celles dont le sens de numérisation est inversé et inverse l'ordre des sommets.
Plus besoin de choisir un seul départ : après le filtre de catégorie, les points restants sont tous des départs, et le sens d'une ligne est décidé par le départ le plus proche.
Deux extrémités comptent comme le même point seulement si elles sont assez proches. Un vide arrête le parcours. Les attributs ne changent pas. Seul l'ordre des sommets est écrit dans le tampon d'édition, et vous enregistrez la couche vous-même.</p>
<p>Le contrôle ne signale qu'un seul type d'erreur : une ligne qu'aucun départ n'atteint. Une ligne qui s'arrête simplement est normal, pas une erreur.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> depuis Sens des lignes sur la barre de la table.</li>
<li><b>Tolérance d'accrochage</b>, en mètres, 0.6 par défaut (modifiable aussi dans Réglages → Paramètres). Si A est près de B et B près de C, les trois extrémités sont un seul point, même si A et C sont plus éloignés que la tolérance. Faites attention là où les extrémités sont denses.</li>
<li><b>Couche de départ</b> : une couche de points. Le bouton de droite filtre par catégorie. Les catégories décochées dans la légende sont quand même listées. Cochez-les pour les inclure. Les points qui passent le filtre agissent tous comme départs en même temps. Un départ qui ne touche aucune extrémité de ligne est ignoré et signalé dans le résultat.</li>
<li><b>Lignes</b> : ajoutez au moins une couche de lignes. Vous pouvez en ajouter plusieurs et filtrer chacune. Le long d'une ligne, le côté départ est le début de la ligne et l'autre côté est la fin.</li>
<li><b>Branches</b> : chaque extrémité de ligne est un nœud. Quand le parcours atteint un point d'où partent plusieurs lignes, il suit chacune vers l'extérieur, en s'éloignant de ce point. Les branches ne sont pas des erreurs.</li>
<li><b>Fins</b>, facultatives, qui ne comptent que là où les lignes forment une boucle : la boucle est coupée à la fin, comme si les lignes ne s'y rejoignaient pas, et les deux côtés vont vers elle. Sans boucle, une fin est inutile et ne change rien ; le parcours la traverse. Sur une boucle sans fin, le départ le plus proche l'emporte et la ligne où les deux côtés se rejoignent n'a pas de sens : c'est une fausse boucle, écrite dans une couche temporaire et non cochée. Exactement une fin, sur un nœud, coupe la boucle. Plusieurs fins, ou une fin au milieu d'une ligne et non sur un nœud (six lignes autour du départ, chacune avec une fin au milieu), ne donnent pas de coupure unique : ces lignes vont aussi dans une couche temporaire et ne sont pas tenues pour correctes.</li>
<li><b>Après Départ</b> : la fenêtre de résultat reste au-dessus et ne bloque pas la carte. Les lignes inversées sont cochées par défaut. Les fausses boucles ne le sont pas. Inverser la sélection ne retourne que les lignes cochées. Une ligne à extrémité ouverte, une ligne jamais reliée, ou une ligne dont les parties ne s'accordent pas, est laissée telle quelle.</li>
<li><b>Couches temporaires</b> : elles marquent les lignes inversées, les fausses boucles et les sens indécis, affichés par défaut, pour les voir sur la carte. Elles restent après la fermeture de la fenêtre de résultat. Retirez-les vous-même si vous n'en avez pas besoin.</li>
</ul>
""",
    ),
)
