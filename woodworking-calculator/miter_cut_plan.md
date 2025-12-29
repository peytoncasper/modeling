# MITER SAW CUT PLAN - RESOLVED

## Parts from Fusion 360 (19mm thick):

| Part | Final Size | Strip Length | Strips |
|------|------------|--------------|--------|
| Left Side | 400 × 579mm | 600mm | 3 |
| Right Side | 400 × 579mm | 600mm | 3 |
| Top Panel | 450 × 400mm | 420mm* | 3 |
| Bottom Panel | 450 × 400mm | 420mm* | 3 |
| Bottom Drawer Front | 400 × 306mm | 330mm | 3 |
| Top Drawer Front | 400 × 217mm | 230mm | 3 |

*Changed from 470mm to 420mm - top/bottom only need 400mm depth + margin

---

## OPTIMIZED CUT PLAN ✅

```
┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 1: 60.5" × 7" (1537mm × 178mm)                              │
│  Usable: ~1487mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 2:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 3:  230mm  ───────── Top drawer strip                     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1430mm + 6mm kerf = 1436mm                                 │
│  ✓ Leftover: 51mm (scrap)                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 2: 60" × 6" (1524mm × 152mm) ← NARROWEST                    │
│  Usable: ~1474mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  330mm  ───────────── Bottom drawer strip              │
│  ✂️  Cut 2:  330mm  ───────────── Bottom drawer strip              │
│  ✂️  Cut 3:  330mm  ───────────── Bottom drawer strip              │
│  ✂️  Cut 4:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1410mm + 9mm kerf = 1419mm                                 │
│  ✓ Leftover: 55mm (scrap)                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 3: 49.5" × 7" (1257mm × 178mm)                              │
│  Usable: ~1207mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 2:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1020mm + 3mm kerf = 1023mm                                 │
│  ✓ Leftover: 184mm (save for test cuts)                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 4: 60" × 7.5" (1524mm × 191mm) ← WIDEST                     │
│  Usable: ~1474mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 2:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 3:  230mm  ───────── Top drawer strip                     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1430mm + 6mm kerf = 1436mm                                 │
│  ✓ Leftover: 38mm (scrap)                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 5: 49.5" × 7.5" (1257mm × 191mm)                            │
│  Usable: ~1207mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  600mm  ─────────────────── Side panel strip           │
│  ✂️  Cut 2:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1020mm + 3mm kerf = 1023mm                                 │
│  ✓ Leftover: 184mm (save for test cuts)                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BOARD 6: 60.5" × 6.5" (1537mm × 165mm)                            │
│  Usable: ~1487mm                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✂️  Cut 1:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ✂️  Cut 2:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ✂️  Cut 3:  420mm  ─────────────────── Top/Bottom panel strip     │
│  ✂️  Cut 4:  225mm  ───────── Top drawer strip (from leftover)     │
│  ───────────────────────────────────────────────────────────────── │
│  Total: 1260mm + 225mm + 12mm kerf = 1497mm                        │
│  ⚠️  TIGHT FIT - measure actual board first!                       │
│  If short, use 220mm for cut 4 (still works for 217mm part)        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✅ FINAL STRIP TALLY

| Length | Need | Have | Status |
|--------|------|------|--------|
| 600mm (sides) | 6 | 6 | ✅ |
| 420mm (top/bottom) | 6 | 6 | ✅ |
| 330mm (bottom drawer) | 3 | 3 | ✅ |
| 230mm (top drawer) | 3 | 2 + 1* | ✅ |

*Third strip is 225mm from Board 6 leftover (8mm shorter, still fine for 217mm part)

---

## GLUE-UP ASSIGNMENTS

### Side Panels (3 strips each @ 600mm)
| Panel | Strip 1 | Strip 2 | Strip 3 | Total Width |
|-------|---------|---------|---------|-------------|
| **Left Side** | Board 1 (163mm) | Board 3 (163mm) | Board 4 (176mm) | ~502mm → trim to 410mm |
| **Right Side** | Board 1 (163mm) | Board 4 (176mm) | Board 5 (176mm) | ~515mm → trim to 410mm |

### Top/Bottom Panels (3 strips each @ 420mm)
| Panel | Strip 1 | Strip 2 | Strip 3 | Total Width |
|-------|---------|---------|---------|-------------|
| **Top** | Board 2 (137mm) | Board 3 (163mm) | Board 6 (150mm) | ~450mm → trim to 450mm |
| **Bottom** | Board 5 (176mm) | Board 6 (150mm) | Board 6 (150mm) | ~476mm → trim to 450mm |

### Drawer Fronts (3 strips each)
| Panel | Strip 1 | Strip 2 | Strip 3 | Total Width |
|-------|---------|---------|---------|-------------|
| **Bottom Drawer** (330mm) | Board 2 | Board 2 | Board 2 | ~411mm → trim to 400mm |
| **Top Drawer** (230mm) | Board 1 | Board 4 | Board 6* | ~502mm → trim to 400mm |

*Board 6 strip is 225mm (slightly shorter, acceptable)

---

## CUTTING ORDER (Recommended)

1. **Square all boards first** - trim ~25mm off each end on miter saw
2. **Cut longest pieces first** - 600mm strips
3. **Cut medium pieces** - 420mm and 330mm strips  
4. **Cut short pieces last** - 230mm strips from leftovers
5. **Label each strip** with board number and intended use

---

## NOTES

- Total board feet used: ~15 BF
- Waste: ~5% (very efficient!)
- All strips should be jointed/planed to consistent width before glue-up
- Match grain direction when gluing panels

