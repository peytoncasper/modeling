# Fusion 360 Parameters & Components Definition
## Rustic Wedding Memory Box

**Date:** 2025-01-01  
**Project:** Rustic Wedding Keepsake Box  
**Size:** Medium (Primary)

---

## 📐 Parameters Definition

### Overall Dimensions (External)

| Parameter Name | Value (mm) | Value (inches) | Description |
|----------------|------------|---------------|-------------|
| `overall_length` | 254.0 | 10.0 | External length of box |
| `overall_width` | 177.8 | 7.0 | External width of box |
| `overall_height` | 88.9 | 3.5 | External height of box |

### Material Thickness

| Parameter Name | Value (mm) | Value (inches) | Description |
|----------------|------------|---------------|-------------|
| `wall_thickness` | 12.7 | 0.5 | Thickness of all wood panels |
| `lid_edge_height` | 19.05 | 0.75 | Height of lid edge pieces |

### Internal Dimensions (Calculated)

| Parameter Name | Formula | Description |
|----------------|---------|-------------|
| `internal_length` | `overall_length - 2 * wall_thickness` | Internal length (241.3 mm) |
| `internal_width` | `overall_width - 2 * wall_thickness` | Internal width (165.1 mm) |
| `internal_depth` | `overall_height - wall_thickness - lid_clearance` | Internal depth (76.2 mm) |

### Clearances & Tolerances

| Parameter Name | Value (mm) | Value (inches) | Description |
|----------------|------------|---------------|-------------|
| `lid_clearance` | 6.35 | 0.25 | Space between lid and box when closed |
| `joint_tolerance` | 0.127 | 0.005 | Gap tolerance for joints |
| `edge_radius` | 0.8 | 0.03125 | Rounded edge radius (1/32") |

### Hardware Dimensions

| Parameter Name | Value (mm) | Description |
|----------------|------------|-------------|
| `hinge_length` | 25.4 | Hinge length (1") |
| `hinge_width` | 19.05 | Hinge width (0.75") |
| `hinge_spacing` | 50.8 | Distance from edge to hinge center (2") |
| `latch_width` | 38.1 | Latch mechanism width (1.5") |
| `latch_height` | 25.4 | Latch mechanism height (1") |

### Joinery Specifications

| Parameter Name | Value (mm) | Description |
|----------------|------------|-------------|
| `finger_width` | 12.7 | Box joint finger width (matches wall_thickness) |
| `finger_count` | 4 | Number of fingers per joint |
| `mortise_depth` | 3.175 | Hinge mortise depth (1/8") |

---

## 🧩 Components Structure

### Component Hierarchy

```
Root Component
├── BaseBox (Component)
│   ├── BasePanel (Body)
│   ├── FrontPanel (Body)
│   ├── BackPanel (Body)
│   ├── LeftSidePanel (Body)
│   └── RightSidePanel (Body)
│
├── Lid (Component)
│   ├── LidTopPanel (Body)
│   ├── LidFrontEdge (Body)
│   ├── LidBackEdge (Body)
│   ├── LidLeftEdge (Body)
│   └── LidRightEdge (Body)
│
└── Hardware (Component) [Optional - for visualization]
    ├── Hinge1 (Body)
    ├── Hinge2 (Body)
    └── LatchAssembly (Body)
```

### Component 1: BaseBox

**Purpose:** Contains all base box panels

**Bodies:**
1. **BasePanel**
   - Dimensions: `overall_length` x `overall_width` x `wall_thickness`
   - Position: Bottom of box
   - Joinery: Box joints on all 4 sides

2. **FrontPanel**
   - Dimensions: `overall_length` x `overall_height` x `wall_thickness`
   - Position: Front face
   - Joinery: Box joints (top and bottom)
   - Hardware: Catch plate location

3. **BackPanel**
   - Dimensions: `overall_length` x `overall_height` x `wall_thickness`
   - Position: Back face
   - Joinery: Box joints (top and bottom)
   - Hardware: Hinge mortises

4. **LeftSidePanel**
   - Dimensions: `overall_width` x `overall_height` x `wall_thickness`
   - Position: Left side
   - Joinery: Box joints (all 4 sides)

5. **RightSidePanel**
   - Dimensions: `overall_width` x `overall_height` x `wall_thickness`
   - Position: Right side
   - Joinery: Box joints (all 4 sides)

### Component 2: Lid

**Purpose:** Contains all lid panels

**Bodies:**
1. **LidTopPanel**
   - Dimensions: `overall_length` x `overall_width` x `wall_thickness`
   - Position: Top surface
   - Engraving: Personalization area (center)
   - Joinery: Box joints on all 4 sides

2. **LidFrontEdge**
   - Dimensions: `overall_length` x `lid_edge_height` x `wall_thickness`
   - Position: Front edge of lid
   - Hardware: Latch plate location

3. **LidBackEdge**
   - Dimensions: `overall_length` x `lid_edge_height` x `wall_thickness`
   - Position: Back edge of lid
   - Hardware: Hinge mortises

4. **LidLeftEdge**
   - Dimensions: `overall_width` x `lid_edge_height` x `wall_thickness`
   - Position: Left edge of lid

5. **LidRightEdge**
   - Dimensions: `overall_width` x `lid_edge_height` x `wall_thickness`
   - Position: Right edge of lid

### Component 3: Hardware (Optional)

**Purpose:** Visualize hardware placement (can be simplified or omitted)

**Bodies:**
1. **Hinge1** - Simplified representation
2. **Hinge2** - Simplified representation
3. **LatchAssembly** - Simplified representation

---

## 📋 Parameter Creation Order

### Step 1: Create Base Parameters

```python
# Overall dimensions
fusion_create_parameter(name="overall_length", value=254.0, unit="mm", comment="External length of box")
fusion_create_parameter(name="overall_width", value=177.8, unit="mm", comment="External width of box")
fusion_create_parameter(name="overall_height", value=88.9, unit="mm", comment="External height of box")

# Material thickness
fusion_create_parameter(name="wall_thickness", value=12.7, unit="mm", comment="Thickness of all wood panels")
fusion_create_parameter(name="lid_edge_height", value=19.05, unit="mm", comment="Height of lid edge pieces")

# Clearances
fusion_create_parameter(name="lid_clearance", value=6.35, unit="mm", comment="Space between lid and box")
fusion_create_parameter(name="edge_radius", value=0.8, unit="mm", comment="Rounded edge radius")
```

### Step 2: Create Calculated Parameters

```python
# Internal dimensions (calculated)
fusion_create_parameter(name="internal_length", value=241.3, unit="mm", comment="Internal length")
fusion_create_parameter(name="internal_width", value=165.1, unit="mm", comment="Internal width")
fusion_create_parameter(name="internal_depth", value=76.2, unit="mm", comment="Internal depth")

# Note: These should ideally be expressions, but Fusion 360 parameters can be set to expressions
# internal_length = overall_length - 2 * wall_thickness
# internal_width = overall_width - 2 * wall_thickness
# internal_depth = overall_height - wall_thickness - lid_clearance
```

### Step 3: Create Hardware Parameters

```python
fusion_create_parameter(name="hinge_length", value=25.4, unit="mm", comment="Hinge length")
fusion_create_parameter(name="hinge_width", value=19.05, unit="mm", comment="Hinge width")
fusion_create_parameter(name="hinge_spacing", value=50.8, unit="mm", comment="Distance from edge to hinge")
```

### Step 4: Create Joinery Parameters

```python
fusion_create_parameter(name="finger_width", value=12.7, unit="mm", comment="Box joint finger width")
fusion_create_parameter(name="finger_count", value=4, unit="", comment="Number of fingers per joint")
fusion_create_parameter(name="mortise_depth", value=3.175, unit="mm", comment="Hinge mortise depth")
```

---

## 🎯 Component Creation Strategy

### Phase 1: Create Components

1. Create `BaseBox` component
2. Create `Lid` component
3. (Optional) Create `Hardware` component

### Phase 2: Build BaseBox Component

1. Create BasePanel sketch → Extrude
2. Create FrontPanel sketch → Extrude
3. Create BackPanel sketch → Extrude
4. Create LeftSidePanel sketch → Extrude
5. Create RightSidePanel sketch → Extrude
6. Add box joints (can be simplified initially)
7. Add hinge mortises to BackPanel
8. Add catch plate location to FrontPanel

### Phase 3: Build Lid Component

1. Create LidTopPanel sketch → Extrude
2. Create LidFrontEdge sketch → Extrude
3. Create LidBackEdge sketch → Extrude
4. Create LidLeftEdge sketch → Extrude
5. Create LidRightEdge sketch → Extrude
6. Add box joints
7. Add hinge mortises to LidBackEdge
8. Add latch plate location to LidFrontEdge
9. Add engraving area sketch on LidTopPanel

### Phase 4: Assembly & Positioning

1. Position Lid relative to BaseBox
2. Add hinge connections (visualization)
3. Add latch connection (visualization)
4. Test lid clearance

---

## 📐 Key Dimensions Reference

### Base Box Panels

| Panel | Length | Width | Height | Notes |
|-------|--------|-------|--------|-------|
| Base | 254.0 mm | 177.8 mm | 12.7 mm | Bottom |
| Front | 254.0 mm | 88.9 mm | 12.7 mm | With catch plate |
| Back | 254.0 mm | 88.9 mm | 12.7 mm | With hinge mortises |
| Left Side | 177.8 mm | 88.9 mm | 12.7 mm | |
| Right Side | 177.8 mm | 88.9 mm | 12.7 mm | |

### Lid Panels

| Panel | Length | Width | Height | Notes |
|-------|--------|-------|--------|-------|
| Top | 254.0 mm | 177.8 mm | 12.7 mm | With engraving |
| Front Edge | 254.0 mm | 19.05 mm | 12.7 mm | With latch plate |
| Back Edge | 254.0 mm | 19.05 mm | 12.7 mm | With hinge mortises |
| Left Edge | 177.8 mm | 19.05 mm | 12.7 mm | |
| Right Edge | 177.8 mm | 19.05 mm | 12.7 mm | |

---

## 🔧 Next Steps

1. ✅ Define parameters (this document)
2. ✅ Define components structure (this document)
3. ⏭️ Create Fusion 360 document
4. ⏭️ Create parameters in Fusion 360
5. ⏭️ Create components
6. ⏭️ Build BaseBox component
7. ⏭️ Build Lid component
8. ⏭️ Add joinery details
9. ⏭️ Add hardware locations
10. ⏭️ Finalize assembly

---

**Status:** Parameters & Components Defined - Ready for Fusion 360 Implementation







