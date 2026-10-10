# -*- coding: utf-8 -*-
"""English help page. Keep this free of Chinese."""

HELP_HTML_EN = """
<h3>Field Remarks Table — help (version __VERSION__)</h3>
<p>Complementary attribute table for vector layers. It does not replace the built-in
QGIS Attribute Table (F6). Open it from the toolbar, <b>Vector &gt; Field Remarks Table</b>,
or the layer context menu.</p>
<ul>
<li><b>Language</b> is the leftmost toolbar button. The first launch follows the QGIS locale, then the system locale. Your choice is remembered. English mode uses short English icons at the same 24 px size.</li>
<li><b>Double-click the row number</b> to select the feature and zoom to it.</li>
<li><b>Click a column header</b> to sort. Numeric text is sorted as numbers.</li>
<li><b>Header right-click</b>: copy column, copy with header, copy for paste-back, paste back, unique values, select duplicates, select blanks, edit remarks.</li>
<li><b>Paste-back</b> keeps feature ids. Edit values only. Do not change the <b>#fid</b> column.</li>
<li><b>Top bar</b>: pin, scope, freeze, filter, search. The second filter box opens when you click anywhere in it, and each value shows how many features have it.</li>
<li><b>Scope</b>: all features, selected, visible on the map, or edited in this session.</li>
<li><b>Fill bar</b> (edit mode only): constant, blanks only, sequence, prefix + sequence, sequence around text, add text, expression, replace.</li>
<li><b>Themes</b>: Default (native QGIS), Sakura pink, Mint. The choice is remembered on this computer.</li>
<li><b>Field remarks</b> opens the pack window. Packs holds New, Delete, and Rename. Import / Export holds both actions. Enable applies the pack to layer fields.</li>
<li><b>Unmatched packs</b>: you can copy the current pack to a new name. Layers and fields that do not match this project are listed and dropped from the copy.</li>
<li><b>Quick naming</b> writes values from categorized or rule-based symbology. It is independent of field remarks.</li>
<li><b>Field mapping copy</b> copies features from one layer to another with a field map. It is placed after KMZ by default.</li>
<li><b>Line direction</b> lets you pick one start point on the map and flip connected lines so they point away from that point. Gaps stop the walk.</li>
<li><b>Toolbar order</b> is the rightmost button. Drag to reorder, uncheck a button to hide it, and insert separators. Reset restores this default order.</li>
<li><b>KMZ / CSV</b>: KMZ can use single, categorized, or graduated symbol colors. CSV can follow the built-in attribute-table column order.</li>
<li><b>Window size</b> is remembered for this QGIS session only.</li>
</ul>
"""
