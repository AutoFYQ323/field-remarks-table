# -*- coding: utf-8 -*-
"""French help. Five pages, same order as the Chinese and English help."""

PAGES = (
    (
        "Table attributaire",
        """
<h3>Rôle</h3>
<p>C'est une table à côté de la table attributaire de QGIS. Elle ne remplace pas F6 et n'utilise pas son raccourci.
Elle sert à voir et modifier une couche vecteur : trier, filtrer, figer une colonne, remplir des valeurs, coller par identifiant et exporter.
Les remarques de champs, le nommage rapide, la copie de champs et le sens des lignes ont chacun leur page.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> : bouton de la barre, <b>Vecteur → Field Remarks Table</b>, ou le menu contextuel de la couche. Sélectionnez d'abord une couche vecteur dans le panneau des couches.</li>
<li><b>Langue</b> : bouton de langue de la barre. Le premier lancement suit la langue de QGIS, puis celle du système, et le choix est mémorisé. Les choix sont le chinois, l'anglais, l'espagnol, le français et l'arabe. Les fenêtres déjà ouvertes de ce module passent tout de suite à la langue choisie. En arabe, les boutons et les titres vont de droite à gauche. Les valeurs du tableau restent de gauche à droite.</li>
<li><b>Double-clic sur le numéro de ligne</b> : sélectionne l'entité et zoome dessus.</li>
<li><b>Clic sur l'en-tête</b> : trie. Un texte qui ressemble à un nombre est trié comme un nombre.</li>
<li><b>Après un tri</b>, la barre d'état montre le total filtré et le total complet des colonnes numériques. Les autres signalent les doublons, sans tenir compte de la casse.</li>
<li><b>Sélection de cellules</b>. Au bout d'une demi-seconde, le même endroit montre le nombre et la somme s'il s'agit de nombres, sinon les doublons.</li>
<li><b>Clic droit sur l'en-tête</b> : copier la colonne, copier avec l'en-tête, copier pour recoller, recoller, valeurs uniques, sélectionner les doublons, sélectionner les vides, ou modifier les remarques. La copie aller-retour met l'identifiant en colonne 1 (l'en-tête commence par #fid). On ne modifie que la colonne 2. L'écriture se fait par identifiant, pas par position. Les dates sont copiées comme 2024-09-01.</li>
<li><b>Clic droit sur le numéro de ligne</b> : sélectionne les lignes affichées, par exemple 10-50, 1-20,35 ou 80- jusqu'à la dernière.</li>
<li><b>Glisser une colonne</b> ne change l'ordre que dans cette fenêtre. L'ordre des champs de la couche ne change pas. Il n'est pas gardé à la fermeture.</li>
<li><b>Barre du haut, de gauche à droite</b> : épingler, emprise, figer, filtre de catégorie ou de champ, filtre de texte. Le texte bleu suit la couche actuelle de la légende. Le rouge garde cette couche. L'emprise peut être toutes les entités, la sélection, le visible sur la carte, ou le modifié dans cette session. Figer garde une colonne à gauche et aligne les lignes. Le filtre a deux listes : catégorie ou champ à gauche, valeurs à droite (une valeur cochée suffit). Le premier élément de droite, Tous, n'ajoute pas de filtre. Le texte filtre à la frappe, après une demi-seconde. Les deux filtres agissent ensemble.</li>
<li><b>Modifications non enregistrées</b> : la cellule devient jaune pâle. Fermer la fenêtre ne pose pas une autre question. Enregistrer et annuler restent dans QGIS.</li>
<li><b>Contrôle à l'écriture</b> : saisie, remplissage, insertion rapide et collage sont vérifiés selon le type du champ. Ce qui ne tient pas est ignoré. Une décimale écrite dans un entier est arrondie. Un texte trop long est listé avant confirmation. Les champs d'expression et les jointures non modifiables sont en lecture seule.</li>
<li><b>Remplissage</b> (édition seulement) : constante, numéro autour du texte, texte ajouté, expression et remplacement. On peut mettre à jour les lignes filtrées ou la sélection. Une constante peut être le nom d'un autre champ : cette colonne est alors copiée. Pour écrire un texte exactement égal à un nom de champ, mettez-le entre apostrophes. Le numéro autour du texte se place avant ou après et garde le texte. La largeur peut être sans zéros, automatique ou fixe. Les zéros ne restent que dans les champs texte. Une cellule vide ne reçoit que le numéro. Le texte ajouté ne change que le texte déjà présent. L'expression est une expression QGIS. Le remplacement est littéral et change toutes les occurrences de la cellule.</li>
<li><b>Tout sélectionner / inverser / effacer</b> : les deux premières agissent sur les lignes de cette table. Effacer vide la sélection de la couche.</li>
<li><b>Largeur de colonne</b> : Ajuster répartit les colonnes dans la fenêtre. Complet les ouvre selon le contenu et peut dépasser la fenêtre. On peut encore tirer une largeur.</li>
<li><b>Copier, couper, coller</b> : Ctrl+C copie les cellules choisies. Copier de la barre copie des entités entières. Pour modifier puis recoller : Copier la colonne (aller-retour). Ne changez pas la colonne #fid. Si les identifiants ne correspondent pas, se répètent, ou si la colonne de valeurs est vide, rien n'est écrit.</li>
<li><b>Exporter</b> : le CSV peut écrire un texte numérique comme un nombre. Le KMZ peut n'exporter que les lignes de cette table et utiliser les couleurs de symbole unique, catégorisé ou gradué. Les symboles par règles ne sont pas colorés. Un échec de transformation des coordonnées est signalé.</li>
<li><b>Gestion des champs</b> : créer, supprimer et renommer. Si le paquet actuel a encore un nom ou des significations pour ce champ, la suppression demande s'il faut aussi supprimer la remarque.</li>
<li><b>Ordre de la barre</b> : le bouton à droite. On peut masquer des boutons et les faire glisser. Le choix est mémorisé sur cet ordinateur. Le nommage rapide n'apparaît sur la barre que si vous le cochez ici.</li>
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
<li><b>La première fois</b> : ouvrez la table et cliquez sur Remarques de champs. Dans Paquets, créez-en un et sélectionnez-le. Le paquet de réserve ne se modifie pas. Choisissez la couche dans la légende, cliquez un champ à gauche, remplissez le nom et les significations, puis cliquez sur Activer.</li>
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
        "Nommage rapide",
        """
<h3>Rôle</h3>
<p>Écrit dans les entités sélectionnées les valeurs de champ tirées d'une symbologie catégorisée ou basée sur des règles. Cela ne dépend pas de l'activation des remarques de champs.
Toutes les classes sont listées, cochées ou non dans la légende. Points, lignes et polygones doivent être du même type de géométrie.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> : dans la table, ouvrez l'ordre de la barre et cochez Afficher le nommage rapide. Un bouton vert apparaît. Le choix est mémorisé sur cet ordinateur et il est arrêté par défaut.</li>
<li><b>Liste</b> : chaque ligne est une classe. Le nombre entre parenthèses est tenu par cette fenêtre. Il est compté à l'ouverture ou au changement de couche, puis ajusté selon ce qui vient d'être écrit. Le total après le nom de la couche est la somme des classes, pour le comparer à la légende QGIS.</li>
<li><b>Cliquer une classe</b> : une confirmation apparaît, sauf si la case d'écriture immédiate est cochée.</li>
<li><b>Épingler la couche</b> est arrêté par défaut. Après avoir épinglé la couche catégorisée A, sélectionner des entités sur A et cliquer une classe ne change que les attributs. Sélectionner sur une autre couche et cliquer une classe copie la géométrie dans A, puis applique cette classe. La couche source ne change pas, et A ne reçoit pas les champs source.</li>
<li><b>Enregistrement automatique</b> est arrêté par défaut, donc on peut encore annuler. Les comptes de la légende changent quand vous enregistrez dans QGIS. « Enregistrer après N secondes » écrit d'abord, puis lance une fois Enregistrer les modifications de la couche après environ N secondes. D'autres clics relancent ce délai et n'enregistrent qu'une fois. Fermer la fenêtre enregistre tout de suite. Cet enregistrement écrit toutes les modifications non enregistrées de la couche et ne peut pas être annulé.</li>
<li><b>Actualiser les comptes de la légende</b> ne s'exécute que sur clic. Il repose le rendu actuel sur la couche pour que QGIS recalcule. Il ne change pas les entités et ne part pas seul.</li>
<li><b>Si une classe ne peut pas être écrite</b>, par exemple un rendu gradué ou une règle sans valeur de champ, le clic explique pourquoi et n'écrit rien.</li>
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
<li><b>Couches</b> : source sur la première ligne, cible sur la seconde. Filtrez les listes par point, ligne ou polygone. La source peut aussi être chargée depuis un fichier vecteur que QGIS sait ouvrir.</li>
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
<p>Partez d'un point que vous choisissez, suivez les lignes connectées, trouvez celles dont le sens de numérisation est inversé, et inversez l'ordre des sommets.
Deux extrémités comptent comme le même point seulement si elles sont assez proches. Un vide arrête le parcours. Les attributs ne changent pas. Seul l'ordre des sommets est écrit dans le tampon d'édition, et vous enregistrez la couche vous-même.</p>
<h3>Mode d'emploi</h3>
<ul>
<li><b>Ouvrir</b> depuis Sens des lignes sur la barre de la table.</li>
<li><b>Tolérance d'accrochage</b>, en mètres. Si A est près de B et B près de C, les trois extrémités sont un seul point, même si A et C sont plus éloignés que la tolérance. Faites attention là où les extrémités sont denses.</li>
<li><b>Couche de départ</b> : une couche de points. Le bouton de droite filtre par catégorie. Les catégories décochées dans la légende sont quand même listées. Cochez-les pour les inclure. Tous signifie tous les points de cette couche.</li>
<li><b>Lignes</b> : ajoutez au moins une couche de lignes. Vous pouvez en ajouter plusieurs et filtrer chacune. Le long d'une ligne, le côté départ est le début de la ligne et l'autre côté est la fin.</li>
<li><b>Fins</b>, facultatives. Le parcours s'arrête à une fin. Sans fin, une ligne n'est pas traitée comme une fausse boucle seulement parce que, en la retirant, un côté devient inaccessible depuis le départ.</li>
<li><b>Choisissez un départ</b> dans la liste. Cherchez par nom ou par identifiant. Départ reste désactivé tant qu'un point n'est pas choisi.</li>
<li><b>Après Départ</b> : la fenêtre de résultat reste au-dessus et ne bloque pas la carte. Les lignes inversées sont cochées par défaut. Les fausses boucles ne le sont pas. Inverser la sélection ne retourne que les lignes cochées. Une ligne à extrémité ouverte, une ligne jamais reliée, ou une ligne dont les parties ne s'accordent pas, est laissée telle quelle.</li>
<li><b>Couches temporaires</b> : elles marquent les départs, les fins ou les problèmes de sens pour les voir sur la carte. Elles restent après la fermeture de la fenêtre de résultat. Retirez-les vous-même si vous n'en avez pas besoin.</li>
</ul>
""",
    ),
)
