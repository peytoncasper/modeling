# Rustic Wedding Memory Box - Project Plan

**Project:** Rustic Wedding Keepsake Box  
**Date Created:** 2024-12-31  
**Status:** Planning Phase  
**Target Market:** Wedding gifts, Anniversary gifts  
**Expected Price:** $100-140  
**Manufacturing Time:** 2-3 hours per box

---

## 📋 Project Overview

### Product Description
A beautifully crafted wooden keepsake box for weddings, rustic farmhouse style, featuring:
- Natural oak wood with visible grain
- Antique brass latch with padlock
- Laser-engraved personalization
- Cream velvet interior lining
- Hinged lid design

### Use Cases
- Wedding gifts
- Anniversary gifts (with "Established [Date]" variation)
- Generic keepsake box (custom message)

### Target Customers
- Wedding guests purchasing gifts
- Couples celebrating anniversaries
- People seeking personalized keepsake boxes

---

## 📐 Dimensions & Sizes

### Size Options

| Size | Length | Width | Height | Use Case |
|------|--------|-------|--------|----------|
| **Small** | 8" | 6" | 3" | Cards, small keepsakes, budget option |
| **Medium** | 10" | 7" | 3.5" | Standard size, most popular |
| **Large** | 12" | 8" | 4" | Photos, larger items, premium option |

### Primary Focus: Medium Size (10" x 7" x 3.5")

**External Dimensions:**
- Length: 10 inches (254 mm)
- Width: 7 inches (177.8 mm)
- Height: 3.5 inches (88.9 mm)

**Internal Dimensions (approximate):**
- Length: 9.5 inches (241.3 mm) - accounting for wall thickness
- Width: 6.5 inches (165.1 mm) - accounting for wall thickness
- Depth: 3 inches (76.2 mm) - accounting for lid clearance

---

## 🧭 Fusion 360 Coordinate System Convention

### World Coordinate Mapping
- **X axis** = Length (254mm) → Left (-X) to Right (+X)
- **Y axis** = Width (177.8mm) → Front (-Y) to Back (+Y)  
- **Z axis** = Height (88.9mm) → Bottom (-Z) to Top (+Z)

### Origin Placement
- **Origin [0, 0, 0]**: Front-left-bottom corner of the box base
- **Box sits ON the XY plane**: Z=0 is the bottom surface, Z=88.9mm is the top
- **All geometry in positive space**: X, Y, Z all positive for main body

### Build Order Strategy
To keep geometry in positive Z space (intuitive orientation):

1. **Base Panel**: Sketch on XY plane at Z=0, extrude UP (+Z) by thickness
2. **Front Panel**: Sketch on XZ plane at Y=0, extrude INTO +Y by thickness
3. **Back Panel**: Sketch on XZ plane at Y=165.1mm, extrude INTO +Y by thickness  
4. **Left Panel**: Sketch on YZ plane at X=0, extrude INTO +X by thickness
5. **Right Panel**: Sketch on YZ plane at X=241.3mm, extrude INTO +X by thickness

### ⚠️ CRITICAL: Sketch Coordinate Gotchas

| Plane | Sketch X maps to | Sketch Y maps to | WARNING |
|-------|------------------|------------------|---------|
| XY    | World +X         | World +Y         | (normal) |
| **XZ**| World +X         | **World -Z**     | **+Y in sketch = DOWN in world!** |
| **YZ**| **World -Z**     | World +Y         | **+X in sketch = DOWN in world!** |

### How to Draw for Correct Positioning

**To create a panel from Z=0 to Z=88.9mm on XZ plane:**
```
Sketch coordinates: corner1=[0, -88.9], corner2=[254, 0]
NOT: corner1=[0, 0], corner2=[254, 88.9] ← This goes into -Z!
```

**ALWAYS use `fusion_suggest_sketch_coords` before drawing on XZ/YZ planes!**
**OR use `fusion_draw_rectangle_3d` which converts world coords to sketch coords automatically!**

### Part World Bounds (Target Positions)

| Part | X Range | Y Range | Z Range |
|------|---------|---------|---------|
| Base Panel | [0, 254] | [0, 177.8] | [0, 12.7] |
| Front Panel | [0, 254] | [0, 12.7] | [12.7, 88.9] |
| Back Panel | [0, 254] | [165.1, 177.8] | [12.7, 88.9] |
| Left Panel | [0, 12.7] | [12.7, 165.1] | [12.7, 88.9] |
| Right Panel | [241.3, 254] | [12.7, 165.1] | [12.7, 88.9] |

---

## 🔲 Construction Style: Lidded Box with Overhang

### Reference Design Analysis

Based on the reference image, this box uses a **simple lidded construction** (NOT box joints):

```
Reference Box Features:
├── Lid sits ON TOP of box walls (overhangs all sides)
├── Simple butt joints at corners (not finger joints)
├── Hinges at back connecting lid to box
├── Hasp latch with padlock on front
├── Engraved text on lid top
└── Clean, elegant aesthetic
```

### Why NOT Box Joints for This Design?

| Feature | Box Joints | Simple Butt Joints |
|---------|------------|-------------------|
| Visual Style | Industrial, busy | Clean, elegant ✓ |
| Complexity | High | Low ✓ |
| Time | Long | Short ✓ |
| Reference Match | ❌ No | ✓ Yes |

**Decision:** Use simple butt joints with lid overhang per reference design.

> **Note:** Box joint pattern is available in `fusion-patterns/box-joints.md` for projects that need mechanical strength.

### Lid Overhang Design

```
Side View:
        ┌─────────────────────────┐  ← Lid overhangs ~6mm per side
        │         LID             │
    ┌───┴─────────────────────┴───┐
    │                             │  ← Box walls (simple corners)
    │        BOX BODY             │
    │                             │
    └─────────────────────────────┘
              ↑ Bottom panel
```

### Updated Part World Bounds

| Part | X Range | Y Range | Z Range | Notes |
|------|---------|---------|---------|-------|
| Bottom | [0, 254] | [0, 177.8] | [0, 12.7] | Base panel |
| Front | [0, 254] | [0, 12.7] | [12.7, 88.9] | Full length |
| Back | [0, 254] | [165.1, 177.8] | [12.7, 88.9] | Full length |
| Left | [0, 12.7] | [12.7, 165.1] | [12.7, 88.9] | Fits between F/B |
| Right | [241.3, 254] | [12.7, 165.1] | [12.7, 88.9] | Fits between F/B |
| **Lid** | [-6, 260] | [-6, 183.8] | [88.9, 101.6] | **Overhangs 6mm all sides** |

### Hardware Mortises

**Hinge Mortises (Back Panel + Lid):**
- 2 hinges, positioned 50mm from each end
- Mortise depth: 2mm
- Hinge size: ~25mm × 20mm

**Latch Mortise (Front Panel):**
- Centered on front panel
- Hasp catch recessed 2mm
- Staple for padlock

### Construction Order (Simplified)

1. **Bottom Panel** - XY plane, extrude +Z
2. **Front Panel** - XZ plane at Y=0, extrude +Y
3. **Back Panel** - XZ plane at Y=165.1, extrude +Y
4. **Left Panel** - YZ plane at X=0, extrude +X
5. **Right Panel** - YZ plane at X=241.3, extrude +X
6. **Lid** - XY offset plane at Z=88.9, extrude +Z (SEPARATE BODY with overhang)
7. **Hinge Mortises** - Cut into back panel and lid
8. **Latch Mortise** - Cut into front panel
9. **Engraving** - Text on lid top surface

> **Pattern Reference:** See `fusion-patterns/lidded-box.md` for detailed construction guide.

---

## 🧩 Component Breakdown

### Base Box Components

#### 1. Base (Bottom Piece)
- **Material:** Oak wood
- **Dimensions:** 10" x 7" x 0.5" (thickness)
- **Function:** Bottom panel of the box
- **Joinery:** Dovetail or box joints on all four sides
- **Finish:** Sanded smooth, natural wood finish

#### 2. Front Panel
- **Material:** Oak wood
- **Dimensions:** 10" x 3.5" x 0.5" (thickness)
- **Function:** Front wall of the box
- **Joinery:** Dovetail or box joints (top and bottom)
- **Hardware:** Bottom part of latch mechanism attached here
- **Finish:** Sanded smooth, natural wood finish

#### 3. Back Panel
- **Material:** Oak wood
- **Dimensions:** 10" x 3.5" x 0.5" (thickness)
- **Function:** Back wall of the box
- **Joinery:** Dovetail or box joints (top and bottom)
- **Hardware:** Hinge attachment points
- **Finish:** Sanded smooth, natural wood finish

#### 4. Left Side Panel
- **Material:** Oak wood
- **Dimensions:** 7" x 3.5" x 0.5" (thickness)
- **Function:** Left side wall
- **Joinery:** Dovetail or box joints (all four sides)
- **Finish:** Sanded smooth, natural wood finish

#### 5. Right Side Panel
- **Material:** Oak wood
- **Dimensions:** 7" x 3.5" x 0.5" (thickness)
- **Function:** Right side wall
- **Joinery:** Dovetail or box joints (all four sides)
- **Finish:** Sanded smooth, natural wood finish

### Lid Components

#### 6. Lid Top Panel
- **Material:** Oak wood
- **Dimensions:** 10" x 7" x 0.5" (thickness)
- **Function:** Top surface of the lid
- **Engraving:** Personalization area (text and date)
- **Finish:** Sanded smooth, natural wood finish, laser-engraved

#### 7. Lid Front Edge
- **Material:** Oak wood
- **Dimensions:** 10" x 0.75" x 0.5" (thickness)
- **Function:** Front edge of lid
- **Hardware:** Top part of latch mechanism attached here
- **Finish:** Sanded smooth, natural wood finish

#### 8. Lid Back Edge
- **Material:** Oak wood
- **Dimensions:** 10" x 0.75" x 0.5" (thickness)
- **Function:** Back edge of lid (hinge attachment)
- **Hardware:** Hinge attachment points
- **Finish:** Sanded smooth, natural wood finish

#### 9. Lid Left Edge
- **Material:** Oak wood
- **Dimensions:** 7" x 0.75" x 0.5" (thickness)
- **Function:** Left side edge of lid
- **Finish:** Sanded smooth, natural wood finish

#### 10. Lid Right Edge
- **Material:** Oak wood
- **Dimensions:** 7" x 0.75" x 0.5" (thickness)
- **Function:** Right side edge of lid
- **Finish:** Sanded smooth, natural wood finish

### Hardware Components

#### 11. Hinges
- **Type:** Brass or antique brass hinges
- **Quantity:** 2 hinges
- **Size:** Small (approximately 1" x 0.75")
- **Function:** Attach lid to back panel
- **Installation:** Recessed into wood

#### 12. Latch Mechanism
- **Type:** Antique brass latch with padlock
- **Components:**
  - Latch plate (attached to lid front)
  - Catch plate (attached to box front)
  - Padlock (antique brass, small)
- **Function:** Secure lid closed
- **Keys:** 2 keys included

### Interior Components

#### 13. Interior Lining
- **Material:** Cream-colored velvet fabric
- **Dimensions:** Cut to fit interior (9.5" x 6.5" + sides)
- **Function:** Protect contents, luxurious feel
- **Installation:** Glued to interior walls and bottom
- **Thickness:** Approximately 1/16" (1.5mm)

#### 14. Optional Divider (Future Enhancement)
- **Material:** Thin wood or fabric-covered divider
- **Dimensions:** 6.5" x 3" (fits width and depth)
- **Function:** Organize contents
- **Status:** Optional add-on

---

## 🔧 Manufacturing Specifications

### Wood Specifications

**Primary Wood:** Oak (Light to Medium Tone)
- **Type:** White Oak or Red Oak
- **Grade:** Select or better (minimal knots)
- **Moisture Content:** 6-8%
- **Thickness:** 0.5" (12.7mm) for all panels
- **Grain:** Visible natural grain preferred for rustic look

**Alternative Woods (for variations):**
- Walnut (darker, premium option)
- Cherry (richer tone)
- Maple (lighter option)

### Joinery Method

**Primary Choice: Box Joints (Finger Joints)**
- **Advantages:**
  - Strong and durable
  - Easier to manufacture than dovetails
  - Can be CNC-cut for consistency
  - Good for production efficiency
- **Joint Size:** 0.5" fingers (matches material thickness)
- **Tolerance:** Tight fit, minimal gaps

**Alternative: Dovetail Joints**
- **Advantages:**
  - Traditional, premium look
  - Very strong
- **Disadvantages:**
  - More time-consuming
  - Requires more skill
- **Status:** Consider for premium version

### Hardware Specifications

**Hinges:**
- Material: Brass or antique brass
- Finish: Antique brass (aged look)
- Size: Small (1" x 0.75" approximate)
- Quantity: 2 per box
- Type: Recessed (hidden) or surface mount
- Screws: Brass screws included

**Latch & Lock:**
- Material: Antique brass
- Type: Latch mechanism with small padlock
- Lock Size: Small (approximately 1.5" x 1")
- Keys: 2 keys per lock
- Installation: Surface mount on front

### Engraving Specifications

**Method:** CNC Engraving (V-bit or ball-nose bit)
- **Depth:** 0.02-0.05" (0.5-1.3mm) - deeper than laser for visibility
- **Bit:** V-bit (60° or 90°) for text, ball-nose for decorative elements
- **Font:** Elegant script font (converted to toolpath)
- **Default Text:** "Our Forever Starts Here"
- **Date Format:** "EST. [Date]" (e.g., "EST. OCT 26, 2024")
- **Personalization Options:**
  - Couple names (optional)
  - Custom message (alternative to default)
  - Date (required for wedding version)
- **Time:** Approximately 5 minutes per box

**Engraving Area:**
- Location: Center of lid top panel
- Size: Approximately 6" x 2" area
- Layout: Text centered, date below
- **CNC Setup:** Requires fixture to hold lid securely during engraving

### Finish Specifications

**Sanding:**
- Grit Progression: 120 → 180 → 220 → 320
- Final Finish: Smooth to touch
- Edges: Slightly rounded (1/32" radius)

**Finish Options:**
1. **Natural (Recommended):**
   - Food-safe oil (linseed, tung, or mineral oil)
   - Enhances natural wood grain
   - Easy to maintain
   - Non-toxic

2. **Light Stain (Optional):**
   - Light oak stain
   - Enhances grain visibility
   - Maintains rustic look

3. **Clear Polyurethane (Optional):**
   - Water-based polyurethane
   - More protection
   - Slightly less natural look

**Final Finish:** Natural oil finish (recommended)

---

## 📊 Material List (Per Box - Medium Size)

### Wood Components

| Component | Quantity | Dimensions | Material | Thickness |
|-----------|----------|------------|----------|-----------|
| Base Panel | 1 | 10" x 7" | Oak | 0.5" |
| Front Panel | 1 | 10" x 3.5" | Oak | 0.5" |
| Back Panel | 1 | 10" x 3.5" | Oak | 0.5" |
| Left Side | 1 | 7" x 3.5" | Oak | 0.5" |
| Right Side | 1 | 7" x 3.5" | Oak | 0.5" |
| Lid Top | 1 | 10" x 7" | Oak | 0.5" |
| Lid Front Edge | 1 | 10" x 0.75" | Oak | 0.5" |
| Lid Back Edge | 1 | 10" x 0.75" | Oak | 0.5" |
| Lid Left Edge | 1 | 7" x 0.75" | Oak | 0.5" |
| Lid Right Edge | 1 | 7" x 0.75" | Oak | 0.5" |

**Total Wood Volume:** Approximately 0.15 board feet per box

### Hardware

| Component | Quantity | Specifications |
|-----------|----------|----------------|
| Hinges | 2 | Antique brass, 1" x 0.75" |
| Latch Plate | 1 | Antique brass, attached to lid |
| Catch Plate | 1 | Antique brass, attached to box |
| Padlock | 1 | Antique brass, small (1.5" x 1") |
| Keys | 2 | Matching keys for padlock |
| Screws | 8-10 | Brass screws for hinges and latch |

### Interior Materials

| Component | Quantity | Specifications |
|-----------|----------|----------------|
| Velvet Fabric | 1 piece | Cream color, cut to fit interior |
| Adhesive | As needed | Fabric glue or spray adhesive |

### Consumables

| Component | Quantity | Specifications |
|-----------|----------|----------------|
| Sandpaper | Various | 120, 180, 220, 320 grit |
| Wood Finish | As needed | Natural oil (linseed/tung) |
| Glue | As needed | Wood glue for joints |

---

## 🛠️ Manufacturing Process

### Step 1: Material Preparation
1. **Select Wood:** Choose oak boards with good grain pattern
2. **Cut to Rough Size:** Cut panels slightly oversized
3. **Plane/Thickness:** Ensure consistent 0.5" thickness
4. **Joint Edges:** Ensure square, straight edges

### Step 2: Cut Components
1. **Base Panel:** Cut to 10" x 7"
2. **Side Panels:** Cut 4 pieces (front, back, left, right)
3. **Lid Top:** Cut to 10" x 7"
4. **Lid Edges:** Cut 4 edge pieces

### Step 3: Joinery
1. **Cut Box Joints:** Use CNC or jig for consistent joints
2. **Test Fit:** Ensure tight, square fit
3. **Dry Assembly:** Test without glue

### Step 4: Engraving
1. **Lid Preparation:** Sand lid top smooth
2. **Laser Engraving:** Engrave text and date
3. **Clean Up:** Remove any charring/residue

### Step 5: Assembly
1. **Glue Base:** Assemble base box (bottom + 4 sides)
2. **Clamp:** Use clamps to ensure square
3. **Lid Assembly:** Assemble lid (top + 4 edges)
4. **Clamp Lid:** Ensure square and flat

### Step 6: Sanding
1. **Rough Sand:** 120 grit to remove glue, smooth joints
2. **Medium Sand:** 180 grit
3. **Fine Sand:** 220 grit
4. **Final Sand:** 320 grit for smooth finish

### Step 7: Hardware Installation
1. **Install Hinges:** Attach to back panel and lid
2. **Install Latch:** Attach latch mechanism to front
3. **Test Fit:** Ensure lid opens/closes smoothly

### Step 8: Interior Lining
1. **Cut Fabric:** Cut velvet to size
2. **Apply Adhesive:** Glue fabric to interior
3. **Smooth:** Ensure no wrinkles or bubbles

### Step 9: Finishing
1. **Apply Oil:** Apply natural oil finish
2. **Wipe Excess:** Remove excess oil
3. **Cure:** Allow to dry/cure

### Step 10: Quality Check
1. **Check Dimensions:** Verify all measurements
2. **Test Hardware:** Ensure latch and hinges work
3. **Check Finish:** Ensure smooth, professional finish
4. **Final Inspection:** Check for defects

---

## ⏱️ Time Estimates

### Per Box (Medium Size)

| Step | Time Estimate | Notes |
|------|---------------|-------|
| Material Preparation | 15 min | Selecting, cutting, planing |
| Cut Components | 20 min | All pieces cut to size |
| Joinery | 30 min | Cutting joints, test fitting |
| Engraving | 10 min | Laser engraving personalization |
| Assembly | 30 min | Gluing, clamping base and lid |
| Sanding | 45 min | All grits, thorough sanding |
| Hardware Installation | 15 min | Hinges, latch, lock |
| Interior Lining | 15 min | Cutting, gluing fabric |
| Finishing | 20 min | Applying oil, wiping |
| Quality Check | 10 min | Final inspection |
| **Total** | **3 hours 10 min** | **Target: 2-3 hours** |

### Batch Production (5 boxes)

| Step | Time Estimate | Efficiency Gain |
|------|---------------|-----------------|
| Material Preparation | 45 min | Batch cutting |
| Cut Components | 60 min | Batch cutting |
| Joinery | 90 min | Batch setup |
| Engraving | 30 min | Batch setup |
| Assembly | 90 min | Batch gluing |
| Sanding | 120 min | Batch sanding |
| Hardware Installation | 45 min | Batch installation |
| Interior Lining | 45 min | Batch cutting |
| Finishing | 60 min | Batch application |
| Quality Check | 30 min | Final inspection |
| **Total** | **9 hours 15 min** | **1.85 hours per box** |

**Efficiency Gain:** ~40% faster in batches

---

## 💰 Cost Analysis (COGS) - **VALIDATED**

> **Note:** COGS validated against market data. See `cogs-validation.md` for detailed analysis.

### Material Costs (Per Box - Medium Size)

| Component | Cost | Notes |
|-----------|------|-------|
| Oak Wood | $0.90 | 0.15 board feet @ $6.00/bf (bulk pricing) |
| Hardware (Hinges) | $4.00 | 2 hinges @ $2.00 each (bulk pricing) |
| Hardware (Latch/Lock) | $7.50 | Latch mechanism ($3) + padlock ($4.50) |
| Velvet Fabric | $2.00 | Cream velvet, 0.25 yd @ $8/yd |
| Wood Glue | $0.50 | Small amount per box |
| Sandpaper | $0.50 | Various grits |
| Finish (Oil) | $1.00 | Natural oil finish |
| CNC Engraving | $0.50 | 5 minutes @ $0.10/min (electricity, bit wear) |
| **Subtotal** | **$16.90** | |

### Labor Costs (CNC Production)

| Component | Time | Rate | Cost |
|-----------|------|------|------|
| Material Prep | 15 min | $20/hour | $5.00 |
| CNC Cutting | 30 min | $20/hour | $10.00 |
| CNC Engraving | 5 min | $20/hour | $1.67 |
| Assembly | 30 min | $20/hour | $10.00 |
| Sanding | 45 min | $20/hour | $15.00 |
| Hardware Installation | 15 min | $20/hour | $5.00 |
| Interior Lining | 15 min | $20/hour | $5.00 |
| Finishing | 20 min | $20/hour | $6.67 |
| Quality Check | 10 min | $20/hour | $3.33 |
| **Subtotal** | **2.5 hours** | | **$61.67** |

### Overhead & Shipping

| Component | Cost | Notes |
|-----------|------|-------|
| Overhead (10%) | $7.86 | Shop, tools, utilities |
| Shipping Materials | $2.25 | Box, padding, label |
| Shipping Cost | $10.00 | USPS Priority Mail |
| **Subtotal** | **$20.11** | |

### **Total COGS: $98.68**

### Market Pricing Validation

**Market Leader:** EngraveMyMemories  
**Price:** $89.95  
**Monthly Sales:** 538 units  
**Monthly Revenue:** $70,273

**Competitor Price Range:** $49.79 - $279.00  
**Average Price:** $93.40  
**Median Price:** $89.95

### Pricing Analysis

| Price Point | COGS | Gross Profit | Gross Margin | Market Position |
|-------------|------|--------------|--------------|-----------------|
| $100 | $98.68 | $1.32 | 1.3% | ⚠️ Break-even |
| $110 | $98.68 | $11.32 | 10.3% | ✅ **Recommended** |
| $115 | $98.68 | $16.32 | 14.2% | ✅ Good |
| $120 | $98.68 | $21.32 | 17.8% | ✅ Excellent |
| $130 | $98.68 | $31.32 | 24.1% | ✅ Premium |

**⚠️ Critical Finding:** Our COGS ($98.68) is **9.7% higher** than market leader price ($89.95). We cannot compete at $89.95 without losing money.

**✅ Recommended Price:** **$110-115** (10-14% margin)
- Ensures profitability
- Competitive with market ($89-154 range)
- Sustainable for business growth
- Allows for price adjustments

**Alternative Strategy:** Target premium segment at $130-140 (25-30% margin) with higher quality positioning.

---

## 🎯 Design Specifications

### Personalization Options

**Default Text:** "Our Forever Starts Here"

**Variations:**
1. **Wedding Version:**
   - Text: "Our Forever Starts Here"
   - Date: "EST. [Wedding Date]"
   - Optional: Couple names

2. **Anniversary Version:**
   - Text: "Established [Date]"
   - Optional: Couple names
   - Optional: Years together

3. **Generic Version:**
   - Text: Custom message
   - Optional: Date
   - Optional: Names

### Engraving Layout

**Position:** Centered on lid top panel

**Layout:**
```
        [Couple Names - Optional]
    Our Forever Starts Here
        EST. [Date]
```

**Font Specifications:**
- Style: Elegant script font
- Size: Text - 0.5" height, Date - 0.3" height
- Spacing: Appropriate line spacing

### Hardware Placement

**Hinges:**
- Location: Back panel and lid back edge
- Position: Centered, approximately 2" from each side
- Recessed: Yes (flush with surface)

**Latch:**
- Location: Front center
- Position: Centered horizontally, top of front panel
- Lock: Padlock attached to latch

---

## 📐 Technical Drawings Needed

### Required Drawings

1. **Overall Dimensions Drawing**
   - External dimensions
   - Internal dimensions
   - Wall thickness
   - Lid clearance

2. **Exploded View**
   - All components separated
   - Joint details
   - Hardware placement

3. **Joinery Detail**
   - Box joint specifications
   - Finger size and spacing
   - Tolerance specifications

4. **Hardware Installation**
   - Hinge placement and sizing
   - Latch placement and sizing
   - Screw locations

5. **Engraving Layout**
   - Text placement
   - Font specifications
   - Spacing guidelines

---

## ✅ Quality Standards

### Dimensional Tolerances

- **Overall Dimensions:** ±1/16" (1.6mm)
- **Squareness:** ±1/32" (0.8mm)
- **Joint Fit:** Tight, no visible gaps
- **Lid Fit:** Snug but not tight, smooth operation

### Finish Standards

- **Smoothness:** No rough spots, smooth to touch
- **Grain:** Natural wood grain visible
- **Finish:** Even application, no drips or runs
- **Hardware:** Properly installed, functional

### Quality Checklist

- [ ] All dimensions within tolerance
- [ ] Box is square
- [ ] Joints tight, no gaps
- [ ] Lid opens/closes smoothly
- [ ] Hardware functions properly
- [ ] Engraving clear and centered
- [ ] Interior lining smooth, no wrinkles
- [ ] Finish even and professional
- [ ] No visible defects or damage

---

## 🚀 Next Steps

### Phase 1: Design & Prototyping
1. [ ] Create technical drawings
2. [ ] Generate CAD files (if using CNC)
3. [ ] Create prototype (1 box)
4. [ ] Test fit and function
5. [ ] Refine based on prototype

### Phase 2: Production Setup
1. [ ] Source materials (wood, hardware, fabric)
2. [ ] Set up jigs/fixtures
3. [ ] Test manufacturing process
4. [ ] Optimize for efficiency

### Phase 3: Launch Preparation
1. [ ] Create product photography
2. [ ] Write Etsy listings
3. [ ] Set pricing
4. [ ] Build initial inventory (5-10 boxes)
5. [ ] Launch on Etsy

---

## 📝 Notes & Considerations

### Manufacturing Considerations
- **CNC vs. Hand:** Consider CNC for consistency and speed
- **Batch Production:** More efficient in batches of 5-10
- **Material Sourcing:** Find reliable oak supplier
- **Hardware Sourcing:** Find antique brass hardware supplier

### Design Considerations
- **Lid Overhang:** Consider slight overhang for easier opening
- **Interior Depth:** Ensure adequate depth for contents
- **Weight:** Consider shipping weight (target <2 lbs)

### Market Considerations
- **Competition:** Research competitor pricing and features
- **Personalization:** Offer multiple text/date options
- **Packaging:** Professional packaging for shipping
- **Photography:** High-quality product photos critical

---

**Status:** Planning Complete - Ready for Design Phase

