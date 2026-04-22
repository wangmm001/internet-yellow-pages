"""as_galaxy — full global AS graph visualization (~100K nodes, desktop-only).

See DESIGN_GALAXY.md one level up (analysis/as_globe/DESIGN_GALAXY.md) for
the overall architecture. Pipeline entry points:

  step10_galaxy_extract         — Neo4j path   (or)
  step10_galaxy_extract_bgpkit  — BGPKit fallback
  step11_galaxy_score           — 3-preset scoring
  step12_galaxy_layout          — SFDP / spring 3D layout (shared across presets)
  step13_galaxy_tiles           — LOD pyramid + octree tiling (per preset)
  step14_galaxy_bundle          — HEB over Louvain communities (per preset)
  step15_galaxy_export          — binary tile emission (per preset)

P1 covers step10–12; P2 adds step13–15.
"""
