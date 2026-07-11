# IC30/IC13 Flattened PCL Command Map

Generated from parser dispatch pointer tables, using the shortest known prefix
for each parser mode. Known meanings are assigned when they match commands
already listed in `notes/pcl4-language.md` or a lowercase final chains to the
same parser family as its uppercase command.

## Normal parser table @0x112a4

| Sequence | Mode | Next mode | Handler | Known meaning |
| --- | ---: | ---: | --- | --- |
| `0x00` | 0 | 0 |  |  |
| `0x07` | 0 | 0 |  |  |
| `0x08` | 0 | 0 | `0x00f2a8` | Backspace |
| `0x09` | 0 | 0 | `0x00f1cc` | Horizontal tab |
| `0x0a` | 0 | 0 | `0x00f08c` | Line feed |
| `0x0b` | 0 | 0 |  |  |
| `0x0c` | 0 | 0 | `0x00f0f0` | Form feed |
| `0x0d` | 0 | 0 | `0x00f02c` | Carriage return |
| `0x0e` | 0 | 0 | `0x00c6b8` | SO selects secondary text slot |
| `0x0f` | 0 | 0 | `0x00c68a` | SI selects primary text slot |
| `0x1a` | 0 | 2 | `0x011ea4` | Control-Z parser prefix |
| `0x1a 0x1a` | 2 | 0 | `0x0120d2` | Control-Z nested byte |
| `0x1a X` | 2 | 0 | `0x01219e` | Control-Z X control pair |
| `ESC` | 0 | 1 | `0x011eb6` | ESC parser prefix |
| `ESC &` | 1 | 5 | `0x011ec8` | Parameterized '&' family prefix |
| `ESC & a` | 5 | 12 | `0x011eda` | Cursor-position '&a' family prefix |
| `ESC & a C` | 12 | 0 | `0x00f39e` | Horizontal column position |
| `ESC & a H` | 12 | 0 | `0x00f416` | Horizontal decipoint position |
| `ESC & a L` | 12 | 0 | `0x00eb58` | Left margin |
| `ESC & a M` | 12 | 0 | `0x00ec0c` | Right margin |
| `ESC & a R` | 12 | 0 | `0x00f560` | Vertical row position |
| `ESC & a V` | 12 | 0 | `0x00f60a` | Vertical decipoint position |
| `ESC & a c` | 12 | 12 | `0x00f39e` | Horizontal column position (lowercase chaining final) |
| `ESC & a h` | 12 | 12 | `0x00f416` | Horizontal decipoint position (lowercase chaining final) |
| `ESC & a l` | 12 | 12 | `0x00eb58` | Left margin (lowercase chaining final) |
| `ESC & a m` | 12 | 12 | `0x00ec0c` | Right margin (lowercase chaining final) |
| `ESC & a r` | 12 | 12 | `0x00f560` | Vertical row position (lowercase chaining final) |
| `ESC & a v` | 12 | 12 | `0x00f60a` | Vertical decipoint position (lowercase chaining final) |
| `ESC & d` | 5 | 0 | `0x012622` | Underline/text attribute tokenizer |
| `ESC & f` | 5 | 17 | `0x011eda` | Macro/cursor-stack '&f' family prefix |
| `ESC & f S` | 17 | 0 | `0x00f75e` | Push/pop cursor position |
| `ESC & f X` | 17 | 0 | `0x00dd08` | Macro control |
| `ESC & f Y` | 17 | 0 | `0x00e112` | Macro ID |
| `ESC & f s` | 17 | 17 | `0x00f75e` | Push/pop cursor position (lowercase chaining final) |
| `ESC & f x` | 17 | 17 | `0x00dd08` | Macro control (lowercase chaining final) |
| `ESC & f y` | 17 | 17 | `0x00e112` | Macro ID (lowercase chaining final) |
| `ESC & k` | 5 | 11 | `0x011eda` | Text-motion '&k' family prefix |
| `ESC & k G` | 11 | 0 | `0x00edf8` | Line termination mode |
| `ESC & k H` | 11 | 0 | `0x00ca8c` | HMI |
| `ESC & k S` | 11 | 0 | `0x00c390` | Pitch mode |
| `ESC & k g` | 11 | 11 | `0x00edf8` | Line termination mode (lowercase chaining final) |
| `ESC & k h` | 11 | 11 | `0x00ca8c` | HMI (lowercase chaining final) |
| `ESC & k s` | 11 | 11 | `0x00c390` | Pitch mode (lowercase chaining final) |
| `ESC & l` | 5 | 10 | `0x011eda` | Page-layout '&l' family prefix |
| `ESC & l A` | 10 | 0 | `0x00fc74` | Page size |
| `ESC & l C` | 10 | 0 | `0x00cb00` | VMI |
| `ESC & l D` | 10 | 0 | `0x00c992` | Lines per inch |
| `ESC & l E` | 10 | 0 | `0x00ece2` | Top margin |
| `ESC & l F` | 10 | 0 | `0x00ea9e` | Text length |
| `ESC & l H` | 10 | 0 | `0x00ef62` | Paper source / page eject |
| `ESC & l L` | 10 | 0 | `0x00ee64` | Perforation skip |
| `ESC & l O` | 10 | 0 | `0x010220` | Orientation |
| `ESC & l P` | 10 | 0 | `0x00f9e8` | Page length in lines |
| `ESC & l V` | 10 | 0 | `0x01280a` | Vertical forms control channel |
| `ESC & l W` | 10 | 0 | `0x011f6e` | Vertical forms control payload |
| `ESC & l X` | 10 | 0 | `0x00eef0` | Number of copies |
| `ESC & l a` | 10 | 10 | `0x00fc74` | Page size (lowercase chaining final) |
| `ESC & l c` | 10 | 10 | `0x00cb00` | VMI (lowercase chaining final) |
| `ESC & l d` | 10 | 10 | `0x00c992` | Lines per inch (lowercase chaining final) |
| `ESC & l e` | 10 | 10 | `0x00ece2` | Top margin (lowercase chaining final) |
| `ESC & l f` | 10 | 10 | `0x00ea9e` | Text length (lowercase chaining final) |
| `ESC & l h` | 10 | 10 | `0x00ef62` | Paper source / page eject (lowercase chaining final) |
| `ESC & l l` | 10 | 10 | `0x00ee64` | Perforation skip (lowercase chaining final) |
| `ESC & l o` | 10 | 10 | `0x010220` | Orientation (lowercase chaining final) |
| `ESC & l p` | 10 | 10 | `0x00f9e8` | Page length in lines (lowercase chaining final) |
| `ESC & l v` | 10 | 10 | `0x01280a` | Vertical forms control channel (lowercase chaining final) |
| `ESC & l w` | 10 | 10 | `0x011f6e` | Vertical forms control payload (lowercase chaining final) |
| `ESC & l x` | 10 | 10 | `0x00eef0` | Number of copies (lowercase chaining final) |
| `ESC & p` | 5 | 9 | `0x011eda` | Transparent-data '&p' family prefix |
| `ESC & p X` | 9 | 0 | `0x011f5a` | Transparent print data |
| `ESC & p x` | 9 | 9 | `0x011f5a` | Transparent print data (lowercase chaining final) |
| `ESC & s` | 5 | 8 | `0x011eda` | Wrap-mode '&s' family prefix |
| `ESC & s C` | 8 | 0 | `0x00edb0` | End-of-line wrap |
| `ESC & s c` | 8 | 8 | `0x00edb0` | End-of-line wrap (lowercase chaining final) |
| `ESC (` | 1 | 4 | `0x01201e` | Primary font family prefix |
| `ESC ( @` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( A` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( B` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( C` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( D` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( E` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( F` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( G` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( H` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( I` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( J` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( K` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( L` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( M` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( N` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( O` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( P` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( Q` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( R` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( S` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( T` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( U` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( V` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( W` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( X` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( Y` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( Z` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( [` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( \` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( ]` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( ^` | 4 | 0 | `0x0120be` | Primary font-designation terminal |
| `ESC ( s` | 4 | 13 | `0x011ff6` | Primary font-selection '(s' family prefix |
| `ESC ( s B` | 13 | 0 | `0x0120aa` | Primary stroke weight |
| `ESC ( s H` | 13 | 0 | `0x012096` | Primary pitch |
| `ESC ( s P` | 13 | 0 | `0x012082` | Primary spacing |
| `ESC ( s S` | 13 | 0 | `0x01206e` | Primary style |
| `ESC ( s T` | 13 | 0 | `0x01205a` | Primary typeface |
| `ESC ( s V` | 13 | 0 | `0x012046` | Primary point size |
| `ESC ( s W` | 13 | 0 | `0x011f96` | Download font/character data |
| `ESC ( s b` | 13 | 13 | `0x00c840` | Primary stroke weight (lowercase chaining final) |
| `ESC ( s h` | 13 | 13 | `0x00c89c` | Primary pitch (lowercase chaining final) |
| `ESC ( s p` | 13 | 13 | `0x00c930` | Primary spacing (lowercase chaining final) |
| `ESC ( s s` | 13 | 13 | `0x00c780` | Primary style (lowercase chaining final) |
| `ESC ( s t` | 13 | 13 | `0x00c7e0` | Primary typeface (lowercase chaining final) |
| `ESC ( s v` | 13 | 13 | `0x00c6ec` | Primary point size (lowercase chaining final) |
| `ESC ( s w` | 13 | 13 | `0x011f96` | Download font/character data (lowercase chaining final) |
| `ESC )` | 1 | 4 | `0x012008` | Secondary font family prefix |
| `ESC ) @` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) A` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) B` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) C` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) D` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) E` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) F` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) G` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) H` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) I` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) J` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) K` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) L` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) M` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) N` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) O` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) P` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) Q` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) R` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) S` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) T` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) U` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) V` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) W` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) X` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) Y` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) Z` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) [` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) \` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) ]` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) ^` | 4 | 0 | `0x0120be` | Secondary font-designation terminal |
| `ESC ) s` | 4 | 13 | `0x011ff6` | Secondary font-selection ')s' family prefix |
| `ESC ) s B` | 13 | 0 | `0x0120aa` | Secondary stroke weight |
| `ESC ) s H` | 13 | 0 | `0x012096` | Secondary pitch |
| `ESC ) s P` | 13 | 0 | `0x012082` | Secondary spacing |
| `ESC ) s S` | 13 | 0 | `0x01206e` | Secondary style |
| `ESC ) s T` | 13 | 0 | `0x01205a` | Secondary typeface |
| `ESC ) s V` | 13 | 0 | `0x012046` | Secondary point size |
| `ESC ) s W` | 13 | 0 | `0x011f96` | Download font/character data |
| `ESC ) s b` | 13 | 13 | `0x00c840` | Secondary stroke weight (lowercase chaining final) |
| `ESC ) s h` | 13 | 13 | `0x00c89c` | Secondary pitch (lowercase chaining final) |
| `ESC ) s p` | 13 | 13 | `0x00c930` | Secondary spacing (lowercase chaining final) |
| `ESC ) s s` | 13 | 13 | `0x00c780` | Secondary style (lowercase chaining final) |
| `ESC ) s t` | 13 | 13 | `0x00c7e0` | Secondary typeface (lowercase chaining final) |
| `ESC ) s v` | 13 | 13 | `0x00c6ec` | Secondary point size (lowercase chaining final) |
| `ESC ) s w` | 13 | 13 | `0x011f96` | Download font/character data (lowercase chaining final) |
| `ESC *` | 1 | 3 | `0x011ec8` | Parameterized '*' family prefix |
| `ESC * b` | 3 | 14 | `0x011eda` | Raster-transfer '*b' family prefix |
| `ESC * b W` | 14 | 0 | `0x011f82` | Transfer raster row bytes |
| `ESC * b w` | 14 | 14 | `0x011f82` | Transfer raster row bytes (lowercase chaining final) |
| `ESC * c` | 3 | 16 | `0x011eda` | Rectangle/font-control '*c' family prefix |
| `ESC * c A` | 16 | 0 | `0x010e68` | Rectangle width dots |
| `ESC * c B` | 16 | 0 | `0x010e22` | Rectangle height dots |
| `ESC * c D` | 16 | 0 | `0x015a56` | Assign font ID |
| `ESC * c E` | 16 | 0 | `0x015a18` | Character code |
| `ESC * c F` | 16 | 0 | `0x016df6` | Font control |
| `ESC * c G` | 16 | 0 | `0x010dce` | Area fill id |
| `ESC * c H` | 16 | 0 | `0x010a40` | Rectangle width decipoints |
| `ESC * c P` | 16 | 0 | `0x010898` | Fill rectangle |
| `ESC * c V` | 16 | 0 | `0x010ae0` | Rectangle height decipoints |
| `ESC * c a` | 16 | 16 | `0x010e68` | Rectangle width dots (lowercase chaining final) |
| `ESC * c b` | 16 | 16 | `0x010e22` | Rectangle height dots (lowercase chaining final) |
| `ESC * c d` | 16 | 16 | `0x015a56` | Assign font ID (lowercase chaining final) |
| `ESC * c e` | 16 | 16 | `0x015a18` | Character code (lowercase chaining final) |
| `ESC * c f` | 16 | 16 | `0x016df6` | Font control (lowercase chaining final) |
| `ESC * c g` | 16 | 16 | `0x010dce` | Area fill id (lowercase chaining final) |
| `ESC * c h` | 16 | 16 | `0x010a40` | Rectangle width decipoints (lowercase chaining final) |
| `ESC * c p` | 16 | 16 | `0x010898` | Fill rectangle (lowercase chaining final) |
| `ESC * c v` | 16 | 16 | `0x010ae0` | Rectangle height decipoints (lowercase chaining final) |
| `ESC * p` | 3 | 18 | `0x011eda` | Dot-position '*p' family prefix |
| `ESC * p X` | 18 | 0 | `0x00f48c` | Horizontal dot position |
| `ESC * p Y` | 18 | 0 | `0x00f692` | Vertical dot position |
| `ESC * p x` | 18 | 18 | `0x00f48c` | Horizontal dot position (lowercase chaining final) |
| `ESC * p y` | 18 | 18 | `0x00f692` | Vertical dot position (lowercase chaining final) |
| `ESC * r` | 3 | 7 | `0x011eda` | Raster-control '*r' family prefix |
| `ESC * r A` | 7 | 0 | `0x01075a` | Start raster graphics |
| `ESC * r B` | 7 | 0 | `0x0107fa` | End raster graphics |
| `ESC * r K` | 7 | 0 | `0x012034` | Stateful raster/tokenizer wrapper |
| `ESC * r a` | 7 | 7 | `0x01075a` | Start raster graphics (lowercase chaining final) |
| `ESC * r b` | 7 | 7 | `0x0107fa` | End raster graphics (lowercase chaining final) |
| `ESC * s` | 3 | 6 | `0x011eda` | Stateful '*s' family prefix |
| `ESC * s ^` | 6 | 0 | `0x012034` | Stateful raster/tokenizer wrapper |
| `ESC * t` | 3 | 15 | `0x011eda` | Raster-resolution '*t' family prefix |
| `ESC * t R` | 15 | 0 | `0x010808` | Raster resolution |
| `ESC * t r` | 15 | 15 | `0x010808` | Raster resolution (lowercase chaining final) |
| `ESC 9` | 1 | 0 | `0x00e9ba` | Clear horizontal margins |
| `ESC =` | 1 | 0 | `0x00f176` | Half-line feed |
| `ESC ?` | 1 | 0 |  |  |
| `ESC E` | 1 | 0 | `0x00cc52` | Printer reset |
| `ESC Y` | 1 | 0 | `0x012536` | Display functions on |
| `ESC Z` | 1 | 0 |  | Display functions off |
| `ESC z` | 1 | 0 | `0x00cd86` | Display functions off |

## Alternate/data parser table @0x116f6

| Sequence | Mode | Next mode | Handler | Known meaning |
| --- | ---: | ---: | --- | --- |
| `0x00` | 0 | 0 |  |  |
| `0x07` | 0 | 0 |  |  |
| `0x08` | 0 | 0 |  | Backspace |
| `0x09` | 0 | 0 |  | Horizontal tab |
| `0x0a` | 0 | 0 |  | Line feed |
| `0x0b` | 0 | 0 |  |  |
| `0x0c` | 0 | 0 |  | Form feed |
| `0x0d` | 0 | 0 |  | Carriage return |
| `0x0e` | 0 | 0 |  | SO selects secondary text slot |
| `0x0f` | 0 | 0 |  | SI selects primary text slot |
| `0x1a` | 0 | 2 | `0x011ea4` | Control-Z parser prefix |
| `0x1a 0x1a` | 2 | 0 | `0x01210c` | Control-Z nested byte |
| `0x1a X` | 2 | 0 | `0x0121b2` | Control-Z X control pair |
| `ESC` | 0 | 1 | `0x011eb6` | ESC parser prefix |
| `ESC &` | 1 | 5 | `0x011ec8` | Parameterized '&' family prefix |
| `ESC & a` | 5 | 12 | `0x011eda` | Cursor-position '&a' family prefix |
| `ESC & a C` | 12 | 0 |  | Horizontal column position |
| `ESC & a H` | 12 | 0 |  | Horizontal decipoint position |
| `ESC & a L` | 12 | 0 |  | Left margin |
| `ESC & a M` | 12 | 0 |  | Right margin |
| `ESC & a R` | 12 | 0 |  | Vertical row position |
| `ESC & a V` | 12 | 0 |  | Vertical decipoint position |
| `ESC & a c` | 12 | 12 | `0x011f4c` | Horizontal column position (lowercase chaining final) |
| `ESC & a h` | 12 | 12 | `0x011f4c` | Horizontal decipoint position (lowercase chaining final) |
| `ESC & a l` | 12 | 12 | `0x011f4c` | Left margin (lowercase chaining final) |
| `ESC & a m` | 12 | 12 | `0x011f4c` | Right margin (lowercase chaining final) |
| `ESC & a r` | 12 | 12 | `0x011f4c` | Vertical row position (lowercase chaining final) |
| `ESC & a v` | 12 | 12 | `0x011f4c` | Vertical decipoint position (lowercase chaining final) |
| `ESC & d` | 5 | 0 |  | Underline/text attribute tokenizer |
| `ESC & f` | 5 | 17 | `0x011eda` | Macro/cursor-stack '&f' family prefix |
| `ESC & f S` | 17 | 0 |  | Push/pop cursor position |
| `ESC & f X` | 17 | 0 | `0x00dd08` | Macro control |
| `ESC & f Y` | 17 | 0 |  | Macro ID |
| `ESC & f s` | 17 | 17 | `0x011f4c` | Push/pop cursor position (lowercase chaining final) |
| `ESC & f x` | 17 | 17 | `0x00dd08` | Macro control (lowercase chaining final) |
| `ESC & f y` | 17 | 17 | `0x011f4c` | Macro ID (lowercase chaining final) |
| `ESC & k` | 5 | 11 | `0x011eda` | Text-motion '&k' family prefix |
| `ESC & k G` | 11 | 0 |  | Line termination mode |
| `ESC & k H` | 11 | 0 |  | HMI |
| `ESC & k S` | 11 | 0 |  | Pitch mode |
| `ESC & k g` | 11 | 11 | `0x011f4c` | Line termination mode (lowercase chaining final) |
| `ESC & k h` | 11 | 11 | `0x011f4c` | HMI (lowercase chaining final) |
| `ESC & k s` | 11 | 11 | `0x011f4c` | Pitch mode (lowercase chaining final) |
| `ESC & l` | 5 | 10 | `0x011eda` | Page-layout '&l' family prefix |
| `ESC & l A` | 10 | 0 |  | Page size |
| `ESC & l C` | 10 | 0 |  | VMI |
| `ESC & l D` | 10 | 0 |  | Lines per inch |
| `ESC & l E` | 10 | 0 |  | Top margin |
| `ESC & l F` | 10 | 0 |  | Text length |
| `ESC & l H` | 10 | 0 |  | Paper source / page eject |
| `ESC & l L` | 10 | 0 |  | Perforation skip |
| `ESC & l O` | 10 | 0 |  | Orientation |
| `ESC & l P` | 10 | 0 |  | Page length in lines |
| `ESC & l T` | 10 | 0 |  | Unimplemented page-layout T slot |
| `ESC & l V` | 10 | 0 |  | Vertical forms control channel |
| `ESC & l W` | 10 | 0 | `0x011f6e` | Vertical forms control payload |
| `ESC & l X` | 10 | 0 |  | Number of copies |
| `ESC & l a` | 10 | 10 | `0x011f4c` | Page size (lowercase chaining final) |
| `ESC & l c` | 10 | 10 | `0x011f4c` | VMI (lowercase chaining final) |
| `ESC & l d` | 10 | 10 | `0x011f4c` | Lines per inch (lowercase chaining final) |
| `ESC & l e` | 10 | 10 | `0x011f4c` | Top margin (lowercase chaining final) |
| `ESC & l f` | 10 | 10 | `0x011f4c` | Text length (lowercase chaining final) |
| `ESC & l h` | 10 | 10 | `0x011f4c` | Paper source / page eject (lowercase chaining final) |
| `ESC & l l` | 10 | 10 | `0x011f4c` | Perforation skip (lowercase chaining final) |
| `ESC & l o` | 10 | 10 | `0x011f4c` | Orientation (lowercase chaining final) |
| `ESC & l p` | 10 | 10 | `0x011f4c` | Page length in lines (lowercase chaining final) |
| `ESC & l t` | 10 | 10 | `0x011f4c` | Unimplemented page-layout T slot (lowercase chaining final) |
| `ESC & l v` | 10 | 10 | `0x011f4c` | Vertical forms control channel (lowercase chaining final) |
| `ESC & l w` | 10 | 10 | `0x011f6e` | Vertical forms control payload (lowercase chaining final) |
| `ESC & l x` | 10 | 10 | `0x011f4c` | Number of copies (lowercase chaining final) |
| `ESC & p` | 5 | 9 | `0x011eda` | Transparent-data '&p' family prefix |
| `ESC & p X` | 9 | 0 | `0x011f5a` | Transparent print data |
| `ESC & p x` | 9 | 9 | `0x011f5a` | Transparent print data (lowercase chaining final) |
| `ESC & s` | 5 | 8 | `0x011eda` | Wrap-mode '&s' family prefix |
| `ESC & s C` | 8 | 0 |  | End-of-line wrap |
| `ESC & s c` | 8 | 8 | `0x011f4c` | End-of-line wrap (lowercase chaining final) |
| `ESC (` | 1 | 4 | `0x011fe4` | Primary font family prefix |
| `ESC ( @` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( A` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( B` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( C` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( D` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( E` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( F` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( G` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( H` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( I` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( J` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( K` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( L` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( M` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( N` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( O` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( P` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( Q` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( R` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( S` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( T` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( U` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( V` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( W` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( X` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( Y` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( Z` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( [` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( \` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( ]` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( ^` | 4 | 0 |  | Primary font-designation terminal |
| `ESC ( s` | 4 | 13 | `0x011ff6` | Primary font-selection '(s' family prefix |
| `ESC ( s B` | 13 | 0 |  | Primary stroke weight |
| `ESC ( s H` | 13 | 0 |  | Primary pitch |
| `ESC ( s P` | 13 | 0 |  | Primary spacing |
| `ESC ( s S` | 13 | 0 |  | Primary style |
| `ESC ( s T` | 13 | 0 |  | Primary typeface |
| `ESC ( s V` | 13 | 0 |  | Primary point size |
| `ESC ( s W` | 13 | 0 | `0x011f96` | Download font/character data |
| `ESC ( s b` | 13 | 13 | `0x011f4c` | Primary stroke weight (lowercase chaining final) |
| `ESC ( s h` | 13 | 13 | `0x011f4c` | Primary pitch (lowercase chaining final) |
| `ESC ( s p` | 13 | 13 | `0x011f4c` | Primary spacing (lowercase chaining final) |
| `ESC ( s s` | 13 | 13 | `0x011f4c` | Primary style (lowercase chaining final) |
| `ESC ( s t` | 13 | 13 | `0x011f4c` | Primary typeface (lowercase chaining final) |
| `ESC ( s v` | 13 | 13 | `0x011f4c` | Primary point size (lowercase chaining final) |
| `ESC ( s w` | 13 | 13 | `0x011f96` | Download font/character data (lowercase chaining final) |
| `ESC )` | 1 | 4 | `0x011fd2` | Secondary font family prefix |
| `ESC ) @` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) A` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) B` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) C` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) D` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) E` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) F` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) G` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) H` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) I` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) J` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) K` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) L` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) M` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) N` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) O` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) P` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) Q` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) R` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) S` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) T` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) U` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) V` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) W` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) X` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) Y` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) Z` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) [` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) \` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) ]` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) ^` | 4 | 0 |  | Secondary font-designation terminal |
| `ESC ) s` | 4 | 13 | `0x011ff6` | Secondary font-selection ')s' family prefix |
| `ESC ) s B` | 13 | 0 |  | Secondary stroke weight |
| `ESC ) s H` | 13 | 0 |  | Secondary pitch |
| `ESC ) s P` | 13 | 0 |  | Secondary spacing |
| `ESC ) s S` | 13 | 0 |  | Secondary style |
| `ESC ) s T` | 13 | 0 |  | Secondary typeface |
| `ESC ) s V` | 13 | 0 |  | Secondary point size |
| `ESC ) s W` | 13 | 0 | `0x011f96` | Download font/character data |
| `ESC ) s b` | 13 | 13 | `0x011f4c` | Secondary stroke weight (lowercase chaining final) |
| `ESC ) s h` | 13 | 13 | `0x011f4c` | Secondary pitch (lowercase chaining final) |
| `ESC ) s p` | 13 | 13 | `0x011f4c` | Secondary spacing (lowercase chaining final) |
| `ESC ) s s` | 13 | 13 | `0x011f4c` | Secondary style (lowercase chaining final) |
| `ESC ) s t` | 13 | 13 | `0x011f4c` | Secondary typeface (lowercase chaining final) |
| `ESC ) s v` | 13 | 13 | `0x011f4c` | Secondary point size (lowercase chaining final) |
| `ESC ) s w` | 13 | 13 | `0x011f96` | Download font/character data (lowercase chaining final) |
| `ESC *` | 1 | 3 | `0x011ec8` | Parameterized '*' family prefix |
| `ESC * b` | 3 | 14 | `0x011eda` | Raster-transfer '*b' family prefix |
| `ESC * b W` | 14 | 0 | `0x011f82` | Transfer raster row bytes |
| `ESC * b w` | 14 | 14 | `0x011f82` | Transfer raster row bytes (lowercase chaining final) |
| `ESC * c` | 3 | 16 | `0x011eda` | Rectangle/font-control '*c' family prefix |
| `ESC * c A` | 16 | 0 |  | Rectangle width dots |
| `ESC * c B` | 16 | 0 |  | Rectangle height dots |
| `ESC * c D` | 16 | 0 |  | Assign font ID |
| `ESC * c E` | 16 | 0 |  | Character code |
| `ESC * c F` | 16 | 0 |  | Font control |
| `ESC * c G` | 16 | 0 |  | Area fill id |
| `ESC * c H` | 16 | 0 |  | Rectangle width decipoints |
| `ESC * c P` | 16 | 0 |  | Fill rectangle |
| `ESC * c V` | 16 | 0 |  | Rectangle height decipoints |
| `ESC * c a` | 16 | 16 | `0x011f4c` | Rectangle width dots (lowercase chaining final) |
| `ESC * c b` | 16 | 16 | `0x011f4c` | Rectangle height dots (lowercase chaining final) |
| `ESC * c d` | 16 | 16 | `0x011f4c` | Assign font ID (lowercase chaining final) |
| `ESC * c e` | 16 | 16 | `0x011f4c` | Character code (lowercase chaining final) |
| `ESC * c f` | 16 | 16 | `0x011f4c` | Font control (lowercase chaining final) |
| `ESC * c g` | 16 | 16 | `0x011f4c` | Area fill id (lowercase chaining final) |
| `ESC * c h` | 16 | 16 | `0x011f4c` | Rectangle width decipoints (lowercase chaining final) |
| `ESC * c p` | 16 | 16 | `0x011f4c` | Fill rectangle (lowercase chaining final) |
| `ESC * c v` | 16 | 16 | `0x011f4c` | Rectangle height decipoints (lowercase chaining final) |
| `ESC * p` | 3 | 18 | `0x011eda` | Dot-position '*p' family prefix |
| `ESC * p X` | 18 | 0 |  | Horizontal dot position |
| `ESC * p Y` | 18 | 0 |  | Vertical dot position |
| `ESC * p x` | 18 | 18 | `0x011f4c` | Horizontal dot position (lowercase chaining final) |
| `ESC * p y` | 18 | 18 | `0x011f4c` | Vertical dot position (lowercase chaining final) |
| `ESC * r` | 3 | 7 | `0x011eda` | Raster-control '*r' family prefix |
| `ESC * r A` | 7 | 0 |  | Start raster graphics |
| `ESC * r B` | 7 | 0 |  | End raster graphics |
| `ESC * r K` | 7 | 0 |  | Stateful raster/tokenizer wrapper |
| `ESC * r a` | 7 | 7 | `0x011f4c` | Start raster graphics (lowercase chaining final) |
| `ESC * r b` | 7 | 7 | `0x011f4c` | End raster graphics (lowercase chaining final) |
| `ESC * s` | 3 | 6 | `0x011eda` | Stateful '*s' family prefix |
| `ESC * s ^` | 6 | 0 |  | Stateful raster/tokenizer wrapper |
| `ESC * t` | 3 | 15 | `0x011eda` | Raster-resolution '*t' family prefix |
| `ESC * t R` | 15 | 0 |  | Raster resolution |
| `ESC * t r` | 15 | 15 | `0x011f4c` | Raster resolution (lowercase chaining final) |
| `ESC 9` | 1 | 0 |  | Clear horizontal margins |
| `ESC =` | 1 | 0 |  | Half-line feed |
| `ESC ?` | 1 | 0 |  |  |
| `ESC E` | 1 | 0 | `0x00cc52` | Printer reset |
| `ESC Y` | 1 | 0 | `0x012120` | Display functions on |
| `ESC Z` | 1 | 0 |  | Display functions off |
| `ESC z` | 1 | 0 |  | Display functions off |
