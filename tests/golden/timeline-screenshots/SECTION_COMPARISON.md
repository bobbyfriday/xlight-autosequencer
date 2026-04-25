# Section comparison: story (final) vs hierarchy (raw analyzer)

## Summary

- **Total songs:** 16
- **Genius-source:** 11 (68%)
- **Heuristic-source:** 5
- **agreement_score populated:** 16/16 (re-built 2026-04-25 to refresh stale stories that predated PR #84)

Each timeline is **70 chars wide**, scaled to song duration:

- **Story** = final section labels in `_story.json` (Genius-aligned when source=genius, otherwise heuristic).
- **Conf** = per-section `agreement_score` from PR #84. `░`=0 (lowest), `▒`=1, `▓`=2-3, `█`=4+. ≥3 sources agreeing is strong consensus.
- **Hier** = raw analyzer output (segmentino + qm_segments) feeding the heuristic path. Higher count = more boundaries the story builder filtered or consolidated.

**Role legend:** I=intro V=verse P=pre_chorus p=post_chorus C=chorus B=bridge O=outro X=instrumental/break S=solo D=breakdown

---

### 01_-_Holiday_Road
_🅖 GENIUS, 2:05, 6 story / 12 hier sections — confidence: high=0 med=4 low=2 zero=0_

```
Story  ( 6): IIIIIIIIIIIIIIIIIIIVVVVVVCCCCCCCCCCCCCCCCVVVVCCCCCCCCCCCCCCCCCCCCCCCCC
Conf       : ▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (12): N         ······AAAAAAAAAAAAAAA·NNNNNNNNNNNNNAAAAAAAAAAAAAAANNNNNNNNNN
```

**Story sequence:** intro → intro → verse → chorus → verse → chorus

### 01_-_Like_Its_Christmas
_🅖 GENIUS, 3:20, 10 story / 21 hier sections — confidence: high=2 med=4 low=3 zero=1_

```
Story  (10): IIIVVVVPPPCCCCCCCCCCCCCVVVPPPPCBCCCCCCCCCCCCCCCCCCCCCCCOOOOOOOOOOOOOOO
Conf       : ███▓▓▓▓▓▓▓░░░░░░░░░░░░░███▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
Hier   (21): NNNNNNNNBBBBAAAAANNNNNAAAAABBBBBAAAANNAAAAANNAAAAANNNNNAAAANNAAAAANNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → chorus → outro

### 01_-_Santa_Tell_Me
_🅖 GENIUS, 3:24, 11 story / 12 hier sections — confidence: high=0 med=7 low=4 zero=0_

```
Story  (11): IIIICCCCCCVVVVVVVPPPPCCCCCCVVVVVVVPPPPCCCCCCCBBBBBBBCCCCCCCCCCCCCCCCOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▓▓▓▓▓▓▓▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒
Hier   (12): NNNNAAAAAABBBBBBBBBBBAAAAAAABBBBBBBBBBAAAAAAANNNNNNNNNNAAAAAAANNNNNNNN
```

**Story sequence:** intro → chorus → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → chorus → outro

### 01_-_Uprisingedit
_🅖 GENIUS, 3:19, 11 story / 25 hier sections — confidence: high=0 med=3 low=7 zero=1_

```
Story  (11): IIIIIIIIIIIIIIIIIVVVVVVVVVVVVVCCCCVVVVVVVVVVVVVVVVVVVCCCCCCCCCCCCCCCOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
Hier   (25): NNNNAAAAAAAAAANNNAAAAAAAAAANNNAAAAA·····NNNAAAAAAAAAAAA······AAAAAANNN
```

**Story sequence:** intro → instrumental_break → verse → verse → chorus → verse → verse → chorus → interlude → chorus → outro

### 02_-_Candy_Cane_Lane
_🅖 GENIUS, 3:32, 10 story / 15 hier sections — confidence: high=0 med=5 low=2 zero=3_

```
Story  (10): IIVVVVVVVVVVPPPPPPPPPPCCppppppppVVVVVVVVVVPPPPPPPPPCCpppppppppppOOOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░░░░░░░░░░░░░░░░
Hier   (15): NNNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA·NNNNNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → post_chorus → verse → pre_chorus → chorus → post_chorus → outro

### 04_-_Carol_Of_The_Bells
_🅷 heuristic, 2:46, 9 story / 11 hier sections — confidence: high=1 med=7 low=1 zero=0_

```
Story  ( 9): IIIIIIIIIIIXXXXXXXXXCCCCCXXXXXXBBBXXXXXXXXXXXXXXXXXCCCCCCCCCPPPCCCCCCC
Conf       : ███████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▓▓▓▓▓▓▓
Hier   (11):            ····················AAAAAAAAAAAAAAAAAAAAAAAAAAAAANNNNNNNNNN
```

**Story sequence:** intro → interlude → chorus → instrumental_break → bridge → instrumental_break → chorus → pre_chorus → chorus

### 04_-_First_Snow
_🅷 heuristic, 3:52, 4 story / 15 hier sections — confidence: high=0 med=4 low=0 zero=0_

```
Story  ( 4): CCCCCCVVVVXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXOOOOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (15): NNNNNNAAAAAAAAAAAABBBBBAAAAAAAAABBBBBNNNNNNNNNNNAAAANNNNNAAAANNNNNNNNN
```

**Story sequence:** chorus → verse → interlude → outro

### 05_-_Let_It_Go_From__Frozen__Soundtrack_Version
_🅷 heuristic, 3:43, 9 story / 17 hier sections — confidence: high=0 med=8 low=1 zero=0_

```
Story  ( 9): IIIICCCCCCVVVVVVVVVVVVVVVVVVVVVVVVVVVPPPPPPPCCCCCCPPCCCCCPPPPPPPCCCCCC
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (17): NNNNNNNNNNBBBBBBBBAAAAAAAANNNNBBBBBBBAAAAAAAACCCCCNNNNNNNAAAAAAAACCCCN
```

**Story sequence:** intro → chorus → verse → pre_chorus → chorus → pre_chorus → chorus → pre_chorus → chorus

### 12_-_Carmina_Burana
_🅖 GENIUS, 2:42, 4 story / 12 hier sections — confidence: high=1 med=0 low=3 zero=0_

```
Story  ( 4): IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
Conf       : █████████████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
Hier   (12): NNNNNNNNNNNNNNNNNAAAAAAAAAAAAAAANNNAAAAAAAAAAAAAAANNNNN·AAAAAAAAAAAAAA
```

**Story sequence:** intro → intro → verse → verse

### 14_-_Ghostbusters
_🅖 GENIUS, 4:05, 13 story / 23 hier sections — confidence: high=0 med=4 low=6 zero=3_

```
Story  (13): IIIIIIIIIIVCCCCCCCCCVVVCVVVBBBVXCCCCCCCCCCCCCCCCCCCCCCVVVVOOOOOOOOOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒░░░░░░░░░░░░
Hier   (23): NNNNNNAAAAANNBBBBBAAAANNNBBBBBAAAANNNNNNAAAANNNNNBBBB NNAAAANNNNNNAAAA
```

**Story sequence:** intro → intro → verse → chorus → verse → chorus → verse → bridge → verse → interlude → chorus → verse → outro

### Believe
_🅖 GENIUS, 4:03, 11 story / 20 hier sections — confidence: high=3 med=6 low=1 zero=1_

```
Story  (11): IIIIVPPPPPPPPPPPPPPPPCCCCCCCVVVVVPPPPPPPPPPCCCCCBBPPPPCCCCCCCCCCCCOOOO
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒███████▓▓▓▓████████████░░░░
Hier   (20): NNNNNNNNNNAAAAAAANNNNBBBBNNNNNAAAAAAAAAAAAAANNNN BBBBBBBBBBBBBBBBNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → pre_chorus → chorus → outro

### Cher-DJ_Play_a_Christmas_Song
_🅖 GENIUS, 3:29, 11 story / 28 hier sections — confidence: high=2 med=8 low=0 zero=1_

```
Story  (11): IIIIIVVVVVVVVVPPPCCCCCCCCCCVVVVVVPPCCCCpBBBBBBBBBBCCCCCCCCpppppppppppp
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██████████▓▓▓▓▓▓▓▓████▓░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (28): NAAAAAAAAAAAAA NNNAAAA····NN AAAANNNAAAA·····AAAANNNNNBBBBBBBBBBBBBBBB
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → post_chorus → bridge → chorus → post_chorus

### Crazy_Train
_🅖 GENIUS, 4:51, 13 story / 24 hier sections — confidence: high=1 med=1 low=6 zero=5_

```
Story  (13): IIIIIIIIIVVVVVVVPPCCCCCCVVVVVVPPCCBBBBBBBBXXXXXXXXXVVVPPCCCCCOOOOOOOOO
Conf       : █████████▒▒▒▒▒▒▒░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░
Hier   (24): NNNNNBBBAAAAAAAAAAAAAAAAAAAAAAAAAAANNNN·CCCCCCC··AAAAAAAAAAAAAANNNNNNN
```

**Story sequence:** intro → verse → pre_chorus → chorus → verse → pre_chorus → chorus → bridge → instrumental_break → verse → pre_chorus → chorus → outro

### Down_with_the_Sickness_-_Disturbed
_🅖 GENIUS, 3:34, 9 story / 18 hier sections — confidence: high=0 med=6 low=2 zero=1_

```
Story  ( 9): IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIICCCVVVVPPPPPPPPPCCCpppB
Conf       : ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓░░░▓
Hier   (18): NNNNNNNNNNNAAAAAAAAAAAAAANNNAAAAAANNNNNNAAAAAANNNNNAAAAAANNNNNNNNNNNNN
```

**Story sequence:** intro → intro → chorus → verse → pre_chorus → chorus → post_chorus → bridge → interlude

### Excision__Sullivan_King_-_Hoist_The_Colours_Remix
_🅷 heuristic, 2:29, 8 story / 8 hier sections — confidence: high=3 med=4 low=1 zero=0_

```
Story  ( 8): IIIIXXXXVVCCCCCCCCCCVVVVVVVVVVVVVPPPPPPPPPXXXXXXXXXXXXXXXXXCCCCCCCCCCC
Conf       : ▓▓▓▓████▓▓██████████▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒█████████████████▓▓▓▓▓▓▓▓▓▓▓
Hier   ( 8): NNNNNNN·AAAAAAAAAAAAAAAAAAAAAAAAANNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN
```

**Story sequence:** intro → interlude → verse → chorus → verse → pre_chorus → instrumental_break → chorus

### mad_russian_christmas
_🅷 heuristic, 4:49, 6 story / 20 hier sections — confidence: high=1 med=5 low=0 zero=0_

```
Story  ( 6): IIIIIXXXXXXXXXXXXXCCCCCCXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXVVVVVVVVVOOOOO
Conf       : ▓▓▓▓▓█████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Hier   (20): NNNNNCCCCCCCCNNNNNBBBNNNAAAAAAAAANNNNAAAAAAAAANNNNNNNBBBNNNNNBBBBNNNNN
```

**Story sequence:** intro → interlude → chorus → interlude → verse → outro
