# Third-party assets and software

## MakeHuman bundled assets — CC0 1.0 Universal

Source: https://github.com/makehumancommunity/makehuman

Pinned commit: `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`.

Included: hm08 base mesh, Asian adult female macro target, universal female target, minor torso/stomach targets, high-poly eye mesh and proxy attachment data, brown eye texture. Their file headers explicitly state the September 2020 CC0 release. Exact inputs and hashes are recorded in `assets/provenance.json`.

Revision 03 also uses the same upstream CC0 fuller-body, shoulder, and covered chest-detail reduction targets listed in the provenance manifest. The 4K sportswear albedo bake and procedural micro-normal texture are original project output, not third-party skin scans.

The upstream `LICENSE.md` sections C and D distinguish CC0 graphical assets and output from AGPL application code. This project redistributes the CC0 data and uses an original independent Blender build script. It does not bundle the MakeHuman application or its program logic. See `licenses/MAKEHUMAN-LICENSE.md` and `licenses/CC0-1.0.txt` for the preserved upstream text.

Upstream asset credits include the MakeHuman Team, Manuel Bastioni, Data Collection AB, Joel Palmius and Jonas Hauquier as listed in the individual source headers. Attribution is provided for provenance; CC0 does not require it.

## Three.js — MIT

Three.js 0.180.0 and its OrbitControls/GLTFLoader are bundled into the HTML. Copyright © 2010–2025 Three.js authors. Full license: `licenses/THREE-MIT.txt`.

## esbuild — MIT (build tool only)

esbuild 0.25.10 is used for bundling and is not required at runtime. Its dependency license is included with the development installation. Copyright © Evan Wallace.

## Original additions

Original viewer code, build scripts, garment construction, hair additions and project documentation are released under the MIT license in `licenses/PROJECT-MIT.txt`. MakeHuman-derived asset data remains available under its CC0 dedication. No publisher's textbook images, proprietary anatomical models or scanned individual likenesses are included.
