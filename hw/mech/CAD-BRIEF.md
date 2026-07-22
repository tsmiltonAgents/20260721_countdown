# CAD brief — 3D visual models for T-MINUS board parts

Origin/units per KiCad model conventions: mm, model origin = footprint
origin on the board surface (Z=0), +Z away from the board. Cosmetic render
models (not fit/tolerance parts); dimensions from the verified datasheets
in designlog.md.

1. `xl_sa2401.step` — XINGLIGHT XL-SA2401SRWC display, origin body centre.
   Body 28.5 × 10 × 3.0: bottom 2.2 grey PBT block, top 0.8 dark-red lens
   slab. Four digit windows (4.2 × 7.4, pitch 5.55, centred) recessed 0.1
   into the lens. 12 signal pads (1.5 wide × 1.5 tall × 0.2) wrapping the
   ±Y faces on 2.54 pitch (6/side) + 4 anchor pads (2.0 wide) at x ±11.43,
   silver.
2. `bs08_holder.step` — MYOUNG BS-08 CR2032 holder, origin cavity centre.
   Steel-gold ring: outer Ø22.3, inner Ø20.3, height 5.3, with a top
   retainer lip overhanging inward to Ø19.0 for the top 1.0 mm. Mouth: 100°
   wedge cut on the −X side down to z=1.5 (cell insertion). (+) terminal
   tab: 3.5 wide × 0.2 thick strip from x=+10 to +14.55 at z 0..0.2. (−)
   spring tabs: two 1.8 × 3.5 × 0.2 tongues near cavity centre at z 0.3.
   Body brown PPA (modelled as the ring), terminals gold.
3. `ts1187a.step` — XKB TS-1187A tactile switch, origin body centre.
   Base 5.1 × 5.1 × 1.2 (dark grey), stainless top plate look, centre
   plunger Ø2.0 × 0.3 proud (total height 1.5). Four silver gull-wing
   terminals 0.7 wide reaching to x ±3.55 at the corners (y ±1.875),
   0.2 thick at z 0..0.2.
4. `cr2032.step` — CR2032 cell, origin centre of underside: Ø20 × 3.2,
   silver, small edge chamfer. (Used only for a "populated" beauty render.)

Validation: `scripts/step` generation + `scripts/inspect refs --facts`
bounding-box checks against the numbers above; visual check via KiCad
raytrace render after attachment (snapshot tool substitute — reported).
