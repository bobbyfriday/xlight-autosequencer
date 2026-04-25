# Section comparison: story (final) vs hierarchy (raw analyzer)

## Summary

- **Total songs:** 16
- **Genius-source:** 11 (68%)
- **Heuristic-source:** 5

Heuristic path is the correct fallback when Genius can't be aligned (instrumentals, mismatched remixes, low-confidence text matches). Per `docs/analysis-pipeline-improvements-2026-04.md` §`Genius coverage`, this rate matches PR #81's measurements after the WhisperX hardening.

---

Each timeline is **70 chars wide**, scaled to song duration.

- **Story** = final section labels in `_story.json` (Genius-aligned when source=genius, otherwise heuristic).
- **Conf** = per-section `agreement_score` from PR #84 (0–7+ multi-source agreement). `░`=0 (lowest), `▒`=1, `▓`=2-3, `█`=4+.
- **Hier** = raw analyzer output (segmentino + qm_segments) that feeds the heuristic path. Higher count = more boundaries the story builder filtered or consolidated.

**Role legend:** I=intro V=verse P=pre_chorus p=post_chorus C=chorus B=bridge O=outro X=instrumental/interlude S=solo D=breakdown/drop

### 01_-_Holiday_Road
_🅖 GENIUS, 2:05, 6 story sections / 12 hier sections_

```
Story  ( 6): IIIIIIIIIIIIIIIIIIIVVVVVVCCCCCCCCCCCCCCCCVVVVCCCCCCCCCCCCCCCCCCCCCCCCC
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (12): N         ······AAAAAAAAAAAAAAA·NNNNNNNNNNNNNAAAAAAAAAAAAAAANNNNNNNNNN
```

**Story sequence:** intro → intro → verse → chorus → verse → chorus

### 01_-_Like_Its_Christmas
_🅖 GENIUS, 3:20, 10 story sections / 21 hier sections_

```
Story  (10): IIIVVVVPPPCCCCCCCCCCCCVVVVPPPPCBCCCCCCCCCCCCCCCCCCCCCCCOOOOOOOOOOOOOOO
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (21): NNNNNNNNBBBBAAAAANNNNNAAAAABBBBBAAAANNAAAAANNAAAAANNNNNAAAANNAAAAANNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → chorus → outro

### 01_-_Santa_Tell_Me
_🅖 GENIUS, 3:24, 11 story sections / 12 hier sections_

```
Story  (11): IIIICCCCCCCVVVVVVPPPPCCCCCCCVVVVVVPPPPCCCCCCCBBBBBBCCCCCCCCCCCCCCCCCOO
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (12): NNNNAAAAAABBBBBBBBBBBAAAAAAABBBBBBBBBBAAAAAAANNNNNNNNNNAAAAAAANNNNNNNN
```

**Story sequence:** intro → chorus → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → chorus → outro

### 01_-_Uprisingedit
_🅖 GENIUS, 3:19, 11 story sections / 25 hier sections_

```
Story  (11): IIIIIIIIIIIIIIIIIVVVVVVVVVVVVVCCCCVVVVVVVVVVVVVVVVVVCCCCCCCOOOOOOOOOOO
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (25): NNNNAAAAAAAAAANNNAAAAAAAAAANNNAAAAA·····NNNAAAAAAAAAAAA······AAAAAANNN
```

**Story sequence:** intro → instrumental_break → verse → verse → chorus → verse → verse → chorus → interlude → chorus → outro

### 02_-_Candy_Cane_Lane
_🅖 GENIUS, 3:32, 10 story sections / 15 hier sections_

```
Story  (10): IIVVVVVVVVVVPPPPPPPPPPCCppppppppVVVVVVVVVVPPPPPPPPPCCpppppppppppOOOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░░░░░░░░░░░░░░░░
Hier   (15): NNNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA·NNNNNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → post_chorus → verse → pre_chorus → chorus → post_chorus → outro

### 04_-_Carol_Of_The_Bells
_🅷 heuristic, 2:46, 9 story sections / 11 hier sections_

```
Story  ( 9): IIIIIIIIIIIXXXXXXXXXCCCCCXXXXXXBBBXXXXXXXXXXXXXXXXXCCCCCCCCCPPPCCCCCCC
Conf       : ███████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓▓
Hier   (11):            ····················AAAAAAAAAAAAAAAAAAAAAAAAAAAAANNNNNNNNNN
```

**Story sequence:** intro → interlude → chorus → instrumental_break → bridge → instrumental_break → chorus → pre_chorus → chorus

### 04_-_First_Snow
_🅷 heuristic, 3:52, 4 story sections / 15 hier sections_

```
Story  ( 4): CCCCCCVVVVXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXOOOOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (15): NNNNNNAAAAAAAAAAAABBBBBAAAAAAAAABBBBBNNNNNNNNNNNAAAANNNNNAAAANNNNNNNNN
```

**Story sequence:** chorus → verse → interlude → outro

### 05_-_Let_It_Go_From__Frozen__Soundtrack_Version
_🅷 heuristic, 3:43, 9 story sections / 17 hier sections_

```
Story  ( 9): IIIICCCCCCVVVVVVVVVVVVVVVVVVVVVVVVVVVPPPPPPPCCCCCCPPCCCCCPPPPPPPCCCCCC
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (17): NNNNNNNNNNBBBBBBBBAAAAAAAANNNNBBBBBBBAAAAAAAACCCCCNNNNNNNAAAAAAAACCCCN
```

**Story sequence:** intro → chorus → verse → pre_chorus → chorus → pre_chorus → chorus → pre_chorus → chorus

### 12_-_Carmina_Burana
_🅖 GENIUS, 2:42, 4 story sections / 12 hier sections_

```
Story  ( 4): IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (12): NNNNNNNNNNNNNNNNNAAAAAAAAAAAAAAANNNAAAAAAAAAAAAAAANNNNN·AAAAAAAAAAAAAA
```

**Story sequence:** intro → intro → verse → verse

### 14_-_Ghostbusters
_🅖 GENIUS, 4:05, 13 story sections / 23 hier sections_

```
Story  (13): IIIIIIIIIIVCCCCCCCCCVVVCVVVBBBBXCCCCCCCCCCCCCCCCCCCCCCVVVVOOOOOOOOOOOO
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (23): NNNNNNAAAAANNBBBBBAAAANNNBBBBBAAAANNNNNNAAAANNNNNBBBB NNAAAANNNNNNAAAA
```

**Story sequence:** intro → intro → verse → chorus → verse → chorus → verse → bridge → verse → interlude → chorus → verse → outro

### Believe
_🅖 GENIUS, 4:03, 11 story sections / 20 hier sections_

```
Story  (11): IIIIVPPPPPPPPPPPPPPPPCCCCCCCVVVVVPPPPPPPPPPCCCCCBBPPPPCCCCCCCCCCCCOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒███████▓▓▓▓████████████░░░░
Hier   (20): NNNNNNNNNNAAAAAAANNNNBBBBNNNNNAAAAAAAAAAAAAANNNN BBBBBBBBBBBBBBBBNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → pre_chorus → chorus → outro

### Cher-DJ_Play_a_Christmas_Song
_🅖 GENIUS, 3:29, 11 story sections / 28 hier sections_

```
Story  (11): IIIIIVVVVVVVVVVPPPCCCCCCCCCVVVVVVPPCCCCpBBBBBBBBBBCCCCCCCCpppppppppppp
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (28): NAAAAAAAAAAAAA NNNAAAA····NN AAAANNNAAAA·····AAAANNNNNBBBBBBBBBBBBBBBB
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → post_chorus → bridge → chorus → post_chorus

### Crazy_Train
_🅖 GENIUS, 4:51, 13 story sections / 24 hier sections_

```
Story  (13): IIIIIIIIIVVVVVVVPPCCCCCCVVVVVVPPCCBBBBBBBBXXXXXXXXXVVVPPCCCCCOOOOOOOOO
Conf       : █████████▒▒▒▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░
Hier   (24): NNNNNBBBAAAAAAAAAAAAAAAAAAAAAAAAAAANNNN·CCCCCCC··AAAAAAAAAAAAAANNNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → instrumental_break → verse → pre_chorus → chorus → outro

### Down_with_the_Sickness_-_Disturbed
_🅖 GENIUS, 3:34, 9 story sections / 18 hier sections_

```
Story  ( 9): IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIICCCVVVVPPPPPPPPPCCCpppB
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓░░░▓
Hier   (18): NNNNNNNNNNNAAAAAAAAAAAAAANNNAAAAAANNNNNNAAAAAANNNNNAAAAAANNNNNNNNNNNNN
```

**Story sequence:** intro → intro → chorus → verse → pre_chorus → chorus → post_chorus → bridge → interlude

### Excision__Sullivan_King_-_Hoist_The_Colours_Remix
_🅷 heuristic, 2:29, 8 story sections / 8 hier sections_

```
Story  ( 8): IIIIXXXXVVCCCCCCCCCCVVVVVVVVVVVVVPPPPPPPPPXXXXXXXXXXXXXXXXXCCCCCCCCCCC
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   ( 8): NNNNNNN·AAAAAAAAAAAAAAAAAAAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN
```

**Story sequence:** intro → interlude → verse → chorus → verse → pre_chorus → instrumental_break → chorus

### mad_russian_christmas
_🅷 heuristic, 4:49, 6 story sections / 20 hier sections_

```
Story  ( 6): IIIIIXXXXXXXXXXXXXCCCCCCXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXVVVVVVVVVOOOOO
Conf       : ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Hier   (20): NNNNNCCCCCCCCNNNNNBBBNNNAAAAAAAAANNNNAAAAAAAAANNNNNNNBBBNNNNNBBBBNNNNN
```

**Story sequence:** intro → interlude → chorus → interlude → verse → outro
