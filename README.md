# LiGeo Perception System - Global Vision Skill਍ഀ
## Overview਍ഀ
LiGeo-Perception is a **text-only AI vision engine** that gives language models without image input a trustworthy way to reason about rendered visual output (HTML, SVG, print/PDF, PNG/JPEG) **without ever seeing pixels**.਍ഀ
The browser renderer acts as a deterministic query engine — it knows ground-truth geometry, colors, fonts, load-state. LiGeo makes the renderer narrate its own geometry over the DevTools Protocol, converts that into a typed **evidence contract**, and lets the reasoning model work with structured facts.਍ഀ
## Quick Start਍ഀ
### Install਍怀怀怀戀愀猀栀ഀ
cd C:\Users\ASUS\Desktop\LiGeo-Perception਍瀀椀瀀 椀渀猀琀愀氀氀 ⴀ攀 ⸀ഀ
```਍ഀ
### Single Image Analysis਍怀怀怀戀愀猀栀ഀ
# Basic analysis਍氀椀最漀 椀洀愀最攀⸀瀀渀最ഀ
਍⌀ 圀椀琀栀 䨀匀伀一 漀甀琀瀀甀琀ഀ
ligo image.png --json out.json਍ഀ
# With B01 book profile (1.15cm margins, A4)਍氀椀最漀 椀洀愀最攀⸀瀀渀最 ⴀⴀ瀀爀漀昀椀氀攀 瀀爀漀昀椀氀攀猀⼀䈀　㄀⸀樀猀漀渀 ⴀⴀ洀愀爀最椀渀ⴀ挀栀攀挀欀ഀ
਍⌀ 倀爀漀挀攀猀猀 攀渀琀椀爀攀 搀椀爀攀挀琀漀爀礀ഀ
ligo books/B01/chapters/C03/assets/figures/ --json out.json਍怀怀怀ഀ
਍⌀⌀⌀ 倀礀琀栀漀渀 䄀倀䤀ഀ
```python਍昀爀漀洀 氀椀最漀开瀀攀爀挀攀瀀琀椀漀渀 椀洀瀀漀爀琀 氀漀愀搀开椀洀愀最攀Ⰰ 氀漀愀搀开愀渀搀开瘀愀氀椀搀愀琀攀Ⰰ 愀渀愀氀礀稀攀开挀漀氀漀爀Ⰰ 愀渀愀氀礀稀攀开瀀椀砀攀氀猀ഀ
from vir_builder import build_vir਍昀爀漀洀 愀瀀愀椀开戀椀琀洀愀瀀 椀洀瀀漀爀琀 爀甀渀 愀猀 愀瀀愀椀开爀甀渀ഀ
਍⌀ 䰀漀愀搀 愀渀搀 瘀愀氀椀搀愀琀攀 愀渀 椀洀愀最攀ഀ
with load_image("image.png") as li:਍    椀渀昀漀 㴀 氀椀⸀椀渀昀漀  ⌀ 洀攀琀愀搀愀琀愀 搀椀挀琀ഀ
    img = li.image   # PIL Image object (use within context)਍ഀ
# Get metadata only (no image in memory)਍爀攀挀漀爀搀Ⰰ 椀猀猀甀攀猀 㴀 氀漀愀搀开愀渀搀开瘀愀氀椀搀愀琀攀⠀∀椀洀愀最攀⸀瀀渀最∀⤀ഀ
਍⌀ 䄀渀愀氀礀稀攀 瀀椀砀攀氀 洀攀琀爀椀挀猀ഀ
metrics = analyze_pixels("image.png")਍ഀ
# Run OCR਍漀挀爀开爀攀猀甀氀琀 㴀 愀渀愀氀礀稀攀开漀挀爀⠀∀椀洀愀最攀⸀瀀渀最∀⤀ഀ
਍⌀ 䈀甀椀氀搀 挀漀洀瀀氀攀琀攀 嘀䤀刀 ⠀嘀椀猀甀愀氀 䤀渀琀攀爀洀攀搀椀愀琀攀 刀攀瀀爀攀猀攀渀琀愀琀椀漀渀⤀ഀ
vir = build_vir(਍    氀愀礀漀甀琀开搀愀琀愀㴀氀愀礀漀甀琀开搀愀琀愀Ⰰഀ
    bitmap_data={"file": str(img_path), "record": record, "issues": []},਍    瀀椀砀攀氀开搀愀琀愀㴀笀∀昀椀氀攀∀㨀 猀琀爀⠀椀洀最开瀀愀琀栀⤀Ⰰ ∀洀攀琀爀椀挀猀∀㨀 洀攀琀爀椀挀猀Ⰰ ∀椀猀猀甀攀猀∀㨀 嬀崀紀Ⰰഀ
    ocr_data={"file": str(img_path), "ocr": ocr_result, "issues": []},਍    愀猀猀攀琀开椀搀㴀∀䈀　㄀ⴀ䌀　㌀ⴀ䘀　㄀∀Ⰰഀ
    project_profile="B01",਍⤀ഀ
਍⌀ 䄀倀䄀䤀 愀猀猀攀猀猀洀攀渀琀ഀ
apai_result = apai_bitmap.run(vir_path="out/vir.json", rubric="default")਍怀怀怀ഀ
਍⌀⌀ 䌀漀洀洀愀渀搀 刀攀昀攀爀攀渀挀攀ഀ
਍簀 䌀漀洀洀愀渀搀 簀 䐀攀猀挀爀椀瀀琀椀漀渀 簀ഀ
|---------|-------------|਍簀 怀氀椀最漀 㰀昀椀氀攀⸀瀀渀最㸀怀 簀 䄀渀愀氀礀稀攀 猀椀渀最氀攀 椀洀愀最攀 簀ഀ
| `ligo images/ --json out.json` | Batch process directory |਍簀 怀氀椀最漀 昀椀氀攀⸀瀀渀最 ⴀⴀ瀀爀漀昀椀氀攀 瀀爀漀昀椀氀攀猀⼀䈀　㄀⸀樀猀漀渀 ⴀⴀ洀愀爀最椀渀ⴀ挀栀攀挀欀怀 簀 䌀栀愀瀀琀攀爀ⴀ猀瀀攀挀椀昀椀挀 洀愀爀最椀渀 挀栀攀挀欀 簀ഀ
| `ligo --profile profiles/B01.json` | Use B01 book profile (A4, 1.15cm margins) |਍ഀ
## Output Structure਍ഀ
Every probe returns a typed JSON envelope:਍ഀ
```json਍笀ഀ
  "schema_version": "1.0.0",਍  ∀琀愀爀最攀琀∀㨀 ∀眀攀戀⼀瀀漀猀琀攀爀猀⼀瀀漀猀琀攀爀ⴀ㈀⸀栀琀洀氀∀Ⰰഀ
  "probe": "layout_probe.js",਍  ∀爀漀漀琀∀㨀 笀∀砀∀㨀 　Ⰰ ∀礀∀㨀 　Ⰰ ∀眀∀㨀 ㈀　㜀㤀Ⰰ ∀栀∀㨀 ㈀㘀㐀㘀紀Ⰰഀ
  "issues": [਍    笀∀琀∀㨀 ∀伀嘀䔀刀䘀䰀伀圀∀Ⰰ ∀搀攀琀∀㨀 ∀挀漀渀琀攀渀琀 挀氀椀瀀瀀攀搀㨀 猀挀爀漀氀氀䠀㴀㌀㄀　㘀 㸀 挀氀椀攀渀琀䠀㴀㈀㘀㐀㘀∀Ⰰ ∀爀攀挀琀∀㨀 笀⸀⸀⸀紀Ⰰ ∀挀漀渀昀∀㨀 　⸀㤀㔀紀ഀ
  ]਍紀ഀ
```਍ഀ
## Evidence Tiers਍ഀ
| Tier | Meaning | Usage |਍簀ⴀⴀⴀⴀⴀⴀ簀ⴀⴀⴀⴀⴀⴀⴀⴀⴀ簀ⴀⴀⴀⴀⴀⴀⴀ簀ഀ
| DETECTED | Direct measurement from renderer/pixel/OCR | Ground truth |਍簀 䐀䔀刀䤀嘀䔀䐀 簀 䄀爀椀琀栀洀攀琀椀挀 漀渀 攀瘀椀搀攀渀挀攀 簀 刀攀焀甀椀爀攀猀 爀攀ⴀ洀攀愀猀甀爀攀洀攀渀琀 愀昀琀攀爀 攀搀椀琀猀 簀ഀ
| INTERPRETED | Model hypothesis — human verification required | Must be re-measured |਍ഀ
## Confidence Bands਍ഀ
| Range | Band | How to Use |਍簀ⴀⴀⴀⴀⴀⴀⴀ簀ⴀⴀⴀⴀⴀⴀ簀ⴀⴀⴀⴀⴀⴀⴀⴀⴀⴀⴀⴀ簀ഀ
| 0.90–1.00 | HIGH | Act on it directly |਍簀 　⸀㜀　ጀ〠⸀㠀㤀 簀 䴀䔀䐀䤀唀䴀 簀 䄀挀琀 眀椀琀栀 焀甀椀挀欀 挀漀渀昀椀爀洀愀琀椀漀渀 簀ഀ
| 0.50–0.69 | LOW | Mention; corroborate before acting |਍簀 　⸀　　ጀ〠⸀㐀㤀 簀 唀一䌀䔀刀吀䄀䤀一 簀 一攀瘀攀爀 愀 昀愀挀琀甀愀氀 挀氀愀椀洀 簀ഀ
਍⌀⌀ 䔀瘀椀搀攀渀挀攀 吀椀攀爀猀 ⠀䐀䔀吀䔀䌀吀䔀䐀⼀䐀䔀刀䤀嘀䔀䐀⼀䤀一吀䔀刀倀刀䔀吀䔀䐀⤀ഀ
਍簀 吀椀攀爀 簀 䐀攀昀椀渀椀琀椀漀渀 簀 唀猀愀最攀 簀ഀ
|------|------------|-------|਍簀 ⨀⨀䐀䔀吀䔀䌀吀䔀䐀⨀⨀ 簀 ∀猀挀爀漀氀氀䠀㴀㌀㄀　㘀 㸀 挀氀椀攀渀琀䠀㴀㈀㘀㐀㘀∀ 簀 䤀渀 琀栀攀 攀瘀椀搀攀渀挀攀 椀琀猀攀氀昀 簀ഀ
| **DERIVED** | "the second figure block overflows the sheet" | Arithmetic on evidence |਍簀 ⨀⨀䤀一吀䔀刀倀刀䔀吀䔀䐀⨀⨀ 簀 ∀洀漀瘀椀渀最 昀椀最甀爀攀猀 猀椀搀攀ⴀ戀礀ⴀ猀椀搀攀 眀椀氀氀 昀椀砀 椀琀∀ 簀 䠀礀瀀漀琀栀攀猀椀猀㬀 洀甀猀琀 戀攀 爀攀ⴀ洀攀愀猀甀爀攀搀 簀ഀ
਍⨀⨀䄀渀 䤀一吀䔀刀倀刀䔀吀䔀䐀 挀氀愀椀洀 琀栀愀琀 栀愀猀 渀漀琀 戀攀攀渀 爀攀ⴀ洀攀愀猀甀爀攀搀 洀愀礀 渀攀瘀攀爀 戀攀 爀攀瀀漀爀琀攀搀 愀猀 搀漀渀攀⸀⨀⨀ഀ
਍⌀⌀ 倀爀漀樀攀挀琀 倀爀漀昀椀氀攀猀ഀ
਍倀爀漀昀椀氀攀猀 搀攀挀氀愀爀攀 瀀攀爀ⴀ瀀爀漀樀攀挀琀 攀砀瀀攀挀琀愀琀椀漀渀猀 猀漀 䈀　㄀ 瘀愀氀甀攀猀 搀漀渀✀琀 氀攀愀欀 椀渀琀漀 漀琀栀攀爀 瀀爀漀樀攀挀琀猀㨀ഀ
਍怀怀怀樀猀漀渀ഀ
{਍  ∀瀀爀漀昀椀氀攀开猀挀栀攀洀愀开瘀攀爀猀椀漀渀∀㨀 ∀㄀⸀　⸀　∀Ⰰഀ
  "profile_id": "B01",਍  ∀瀀爀漀昀椀氀攀开渀愀洀攀∀㨀 ∀䈀　㄀ ᐀†䘀漀甀渀搀愀琀椀漀渀猀 漀昀 䄀䤀 䔀渀最椀渀攀攀爀椀渀最∀Ⰰഀ
  "page": {਍    ∀猀椀稀攀∀㨀 笀∀眀椀搀琀栀开挀洀∀㨀 ㈀㄀⸀　Ⰰ ∀栀攀椀最栀琀开挀洀∀㨀 ㈀㤀⸀㜀Ⰰ ∀渀愀洀攀∀㨀 ∀䄀㐀∀紀Ⰰഀ
    "orientation": "portrait",਍    ∀洀愀爀最椀渀猀∀㨀 笀∀琀漀瀀∀㨀 ∀㄀⸀㄀㔀挀洀∀Ⰰ ∀爀椀最栀琀∀㨀 ∀㄀⸀㄀㔀挀洀∀Ⰰ ∀戀漀琀琀漀洀∀㨀 ∀㄀⸀㄀㔀挀洀∀Ⰰ ∀氀攀昀琀∀㨀 ∀㄀⸀㄀㔀挀洀∀紀Ⰰഀ
    "margin_tolerance_mm": 0.5਍  紀Ⰰഀ
  "checks": {"layout": true, "print": true, "margin": true, "accessibility": true},਍  ∀爀甀戀爀椀挀∀㨀 笀∀爀甀戀爀椀挀开椀搀∀㨀 ∀䄀倀䄀䤀ⴀ䈀　㄀ⴀ䤀䰀䰀唀匀吀刀䄀吀䤀伀一ⴀ　　㄀∀Ⰰ ∀爀甀戀爀椀挀开瘀攀爀猀椀漀渀∀㨀 ∀㄀⸀　⸀　∀紀Ⰰഀ
  "gates": {"l3_requires_human_review": true}਍紀ഀ
```਍ഀ
Use with: `ligo image.png --profile profiles/B01.json --margin-check`਍ഀ
## Requirements਍ഀ
- Python 3.8+਍ⴀ 倀椀氀氀漀眀 㸀㴀 㤀⸀　⸀　ഀ
- NumPy >= 1.24.0਍ⴀ 伀瀀攀渀䌀嘀 ⠀漀瀀琀椀漀渀愀氀Ⰰ 昀漀爀 愀搀瘀愀渀挀攀搀 猀攀渀猀漀爀猀⤀ഀ
- Tesseract (optional, for OCR)਍ഀ
## Critical Limitation਍ഀ
**This is a text-only AI vision system.** It cannot read images directly. It works with **renderer-accessible content** (HTML, SVG, print/PDF) via CDP automation, and **bitmap images** via deterministic pixel analysis. It **cannot** perform semantic vision (object recognition, scene understanding, aesthetic judgment) without a separate VLM.਍ഀ
**For semantic vision:** Configure a remote VLM endpoint or install a local VLM library. See `vision_adapter.py` for integration.਍ഀ
## File Structure਍ഀ
```਍䰀椀䜀攀漀ⴀ倀攀爀挀攀瀀琀椀漀渀⼀ഀ
├── ligo_perception/          # Core Python package਍Ȁ‥  ᰀ%%‥开开椀渀椀琀开开⸀瀀礀ഀ
│   ├── cli.py                # CLI entry point਍Ȁ‥  ᰀ%%‥挀瘀开挀漀爀攀⸀瀀礀            ⌀ 匀栀愀爀攀搀 椀洀愀最攀 瀀爀漀挀攀猀猀椀渀最 挀漀爀攀ഀ
│   ├── bitmap_check.py       | PNG/JPEG loader + validation਍Ȁ‥  ᰀ%%‥瀀椀砀攀氀开挀栀攀挀欀⸀瀀礀        簀 䐀攀琀攀爀洀椀渀椀猀琀椀挀 瀀椀砀攀氀 洀攀琀爀椀挀猀 ⠀㄀　 挀愀琀攀最漀爀椀攀猀⤀ഀ
|   | ocr_adapter.py       | Tesseract OCR adapter |਍簀   簀 瘀椀猀椀漀渀开愀搀愀瀀琀攀爀⸀瀀礀   簀 倀氀甀最最愀戀氀攀 嘀䰀䴀 椀渀琀攀爀昀愀挀攀 簀ഀ
|   | capability_detector.py | Capability reporting |਍簀   簀 瘀椀爀开戀甀椀氀搀攀爀⸀瀀礀        簀 嘀䤀刀 戀甀椀氀搀攀爀 簀ഀ
|   | apai_bitmap.py     | APAI rubric-based art/illustration evaluation |਍簀   簀 瀀爀漀昀椀氀攀开氀漀愀搀攀爀⸀瀀礀 簀 匀栀愀爀攀搀 瀀爀漀昀椀氀攀 氀漀愀搀椀渀最⼀瘀愀氀椀搀愀琀椀漀渀 簀ഀ
| tools/                      | Additional tools |਍簀   ᰀ%%‥挀搀瀀开爀甀渀渀攀爀⸀瀀礀      簀 䌀䐀倀 戀爀漀眀猀攀爀 琀爀愀渀猀瀀漀爀琀 簀ഀ
|   ├── layout_check.py    | Geometry probes over files/dirs |਍簀   ᰀ%%‥愀㄀㄀礀开挀栀攀挀欀⸀瀀礀      簀 愀砀攀ⴀ挀漀爀攀 圀䌀䄀䜀 ⬀ 昀漀挀甀猀 瀀爀漀戀攀 簀ഀ
|   ├── print_check.py     | printToPDF size/page-count assertions |਍簀   ᰀ%%‥瀀搀昀开挀栀攀挀欀⸀瀀礀       簀 倀䐀䘀 瀀愀最攀猀⼀瀀愀瀀攀爀 猀椀稀攀 簀ഀ
|   ├── identify.py        | Image identification |਍簀   ᰀ%%‥挀漀洀瀀椀氀攀⸀瀀礀         簀 䌀漀洀瀀椀氀攀 猀挀爀椀瀀琀猀 簀ഀ
|   └── README.md          | Tools documentation |਍簀 瀀爀漀戀攀猀⼀              簀 䨀愀瘀愀匀挀爀椀瀀琀 瀀爀漀戀攀猀 昀漀爀 䌀䐀倀 簀ഀ
|   ├── layout_probe.js      | Layout geometry probes |਍簀   ᰀ%%‥猀瘀最开瀀爀漀戀攀⸀樀猀       簀 匀嘀䜀 挀愀渀瘀愀猀 挀氀椀瀀瀀椀渀最Ⰰ 琀攀砀琀 挀漀氀氀椀猀椀漀渀猀 簀ഀ
|   ├── image_probe.js       | Rendered image probing |਍簀   ᐀%%‥瀀愀最攀开洀愀爀最椀渀开瀀爀漀戀攀⸀樀猀 簀 䌀匀匀 䀀瀀愀最攀 洀愀爀最椀渀 椀渀猀瀀攀挀琀椀漀渀 簀ഀ
| profiles/          | Project profiles |਍簀   ᰀ%%‥䈀　㄀⸀樀猀漀渀         簀 䈀　㄀ 戀漀漀欀 瀀爀漀昀椀氀攀 ⠀䄀㐀Ⰰ ㄀⸀㄀㔀挀洀 洀愀爀最椀渀猀⤀ 簀ഀ
|   └── generic.json     | Generic document profile |਍簀 琀攀猀琀猀⼀             簀 吀攀猀琀 猀甀椀琀攀 簀ഀ
|   ├── test_cv_core.py              | cv_core tests |਍簀   簀 琀攀猀琀开戀椀琀洀愀瀀开挀栀攀挀欀⸀瀀礀      簀 戀椀琀洀愀瀀开挀栀攀挀欀 琀攀猀琀猀 簀ഀ
|   | test_pixel_check.py        | pixel_check tests |਍簀   簀 琀攀猀琀开漀挀爀开愀搀愀瀀琀攀爀⸀瀀礀         簀 漀挀爀开愀搀愀瀀琀攀爀 琀攀猀琀猀 簀ഀ
|   | test_color_sensor.py     | color_sensor tests |਍簀   簀 琀攀猀琀开攀搀最攀开猀攀渀猀漀爀⸀瀀礀       簀 攀搀最攀开猀攀渀猀漀爀 琀攀猀琀猀 簀ഀ
|   | test_quality_sensor.py    | quality_sensor tests |਍簀   簀 琀攀猀琀开最攀漀洀攀琀爀礀开猀攀渀猀漀爀⸀瀀礀   簀 最攀漀洀攀琀爀礀开猀攀渀猀漀爀 琀攀猀琀猀 簀ഀ
|   | test_similarity_sensor.py   | similarity_sensor tests |਍簀   簀 琀攀猀琀开爀攀最椀猀琀爀愀琀椀漀渀开猀攀渀猀漀爀⸀瀀礀 簀 爀攀最椀猀琀爀愀琀椀漀渀开猀攀渀猀漀爀 琀攀猀琀猀 簀ഀ
|   | test_region_sensor.py       | region_sensor tests |਍簀   簀 琀攀猀琀开搀漀挀甀洀攀渀琀开猀攀渀猀漀爀⸀瀀礀   簀 搀漀挀甀洀攀渀琀开猀攀渀猀漀爀 琀攀猀琀猀 簀ഀ
|   | test_diagram_sensor.py    | diagram_sensor tests |਍簀   簀 琀攀猀琀开椀氀氀甀猀琀爀愀琀椀漀渀开猀攀渀猀漀爀⸀瀀礀 簀 椀氀氀甀猀琀爀愀琀椀漀渀开猀攀渀猀漀爀 琀攀猀琀猀 簀ഀ
|   | test_pdf_text_adapter.py   | pdf_text_adapter tests |਍簀   簀 琀攀猀琀开瘀椀爀开戀甀椀氀搀攀爀⸀瀀礀       簀 瘀椀爀开戀甀椀氀搀攀爀 琀攀猀琀猀 簀ഀ
|   └── test_integration.py   | Integration tests |਍簀 昀椀砀琀甀爀攀猀⼀           簀 吀攀猀琀 愀猀猀攀琀猀 簀ഀ
|   ├── clean.png           | Clean image (white background) |਍簀   簀 氀椀渀攀开愀爀琀⸀瀀渀最         簀 䰀椀渀攀 愀爀琀 昀漀爀 攀搀最攀 搀攀琀攀挀琀椀漀渀 簀ഀ
|   | low_contrast.png        | Low contrast image |਍簀   簀 爀漀琀愀琀攀搀⸀瀀渀最             簀 刀漀琀愀琀攀搀 挀漀渀琀攀渀琀 簀ഀ
|   | text_image.png          | Text image for OCR |਍簀   簀 琀攀砀琀开栀攀愀瘀礀⸀瀀渀最          簀 䴀甀氀琀椀瀀氀攀 琀攀砀琀 氀椀渀攀猀 簀ഀ
|   | duplicate_pair_1.png    | Duplicate pair 1 |਍簀   簀 搀甀瀀氀椀挀愀琀攀开瀀愀椀爀开㈀⸀瀀渀最    簀 䐀甀瀀氀椀挀愀琀攀 瀀愀椀爀 ㈀ 簀ഀ
|   | scanned_page.png        | Scanned page |਍簀   簀 瘀椀漀氀愀琀椀漀渀猀⸀瀀渀最          簀 嘀椀漀氀愀琀椀漀渀 椀洀愀最攀 簀ഀ
| docs/             | Documentation |਍簀   ᰀ%%‥䄀刀䌀䠀䤀吀䔀䌀吀唀刀䔀⸀洀搀   簀 匀礀猀琀攀洀 愀爀挀栀椀琀攀挀琀甀爀攀 簀ഀ
|   | PLAYBOOK.md           | Operating manual |਍簀   簀 䔀嘀䤀䐀䔀一䌀䔀ⴀ匀䌀䠀䔀䴀䄀⸀洀搀   簀 䔀瘀椀搀攀渀挀攀 挀漀渀琀爀愀挀琀 簀ഀ
|   | INTEGRATION.md   | Integration guide |਍簀   簀 䘀䰀伀圀䌀䠀䄀刀吀匀⸀洀搀   簀 䄀匀䌀䤀䤀 昀氀漀眀挀栀愀爀琀猀 簀ഀ
|   | upgrade/            | Upgrade documentation |਍簀   簀   簀 䰀䤀䜀䔀伀开䌀倀唀开嘀䤀匀䤀伀一开䄀唀䐀䤀吀⸀洀搀 簀ഀ
|   |   | LIEGO_COMPONENT_INVENTORY.md |਍簀   簀   簀 䰀䤀䔀䜀伀开匀䌀䠀䔀䴀䄀开䌀伀䴀倀䄀吀䤀䈀䤀䰀䤀吀夀⸀洀搀 簀ഀ
|   |   | LIEGO_TEST_BASELINE.md |਍簀   簀   簀 䰀䤀䔀䜀伀开䘀䤀一䄀䰀开䜀䄀倀匀开刀䔀倀伀刀吀⸀洀搀 簀ഀ
| setup.py            | Package setup |਍簀 刀䔀䄀䐀䴀䔀⸀洀搀           簀 吀栀椀猀 昀椀氀攀 簀ഀ
| .gitignore          | Git ignore |਍簀 刀䔀䄀䐀䴀䔀⸀洀搀           簀 吀栀椀猀 昀椀氀攀 簀ഀ
```਍ഀ
---਍ഀ
## Integration with AI Engineering Book Series਍ഀ
This system is designed for the AI Engineering Book Series (B01-B18). Each book chapter can use LiGeo for:਍ഀ
- **Chapter figures**: Verify layout, overlap, overflow਍ⴀ ⨀⨀吀愀戀氀攀猀⨀⨀㨀 嘀攀爀椀昀礀 愀氀椀最渀洀攀渀琀Ⰰ 漀瘀攀爀昀氀漀眀ഀ
- **Worksheets**: Verify layout, accessibility਍ⴀ ⨀⨀倀爀愀挀琀椀挀愀氀猀⨀⨀㨀 嘀攀爀椀昀礀 氀愀礀漀甀琀Ⰰ 愀挀挀攀猀猀椀戀椀氀椀琀礀ഀ
- **Print books**: Verify page margins, page count, page size਍ഀ
### Example: B01 Chapter 03 Production਍ഀ
```bash਍⌀ 䌀栀攀挀欀 挀栀愀瀀琀攀爀 昀椀最甀爀攀猀ഀ
ligo books/B01/chapters/C03/assets/figures/*.png --json out/figures.json਍ഀ
# Check page layout਍氀椀最漀 戀漀漀欀猀⼀䈀　㄀⼀挀栀愀瀀琀攀爀猀⼀䌀　㌀⼀䈀　㄀开䌀　㌀⸀栀琀洀氀 ⴀⴀ瀀爀漀昀椀氀攀 瀀爀漀昀椀氀攀猀⼀䈀　㄀⸀樀猀漀渀 ⴀⴀ洀愀爀最椀渀ⴀ挀栀攀挀欀 ⴀⴀ瀀爀椀渀琀ഀ
਍⌀ 䈀甀椀氀搀 嘀䤀刀 昀漀爀 挀栀愀瀀琀攀爀ഀ
python tools/vir_builder.py \਍    ⴀⴀ氀愀礀漀甀琀 漀甀琀⼀氀愀礀漀甀琀⸀樀猀漀渀 尀ഀ
    --bitmap out/bitmap.json \਍    ⴀⴀ瀀椀砀攀氀猀 漀甀琀⼀瀀椀砀攀氀猀⸀樀猀漀渀 尀ഀ
    --ocr out/ocr.json \਍    ⴀⴀ愀猀猀攀琀ⴀ椀搀 ∀䈀　㄀ⴀ䌀　㌀ⴀ䘀　㄀∀ 尀ഀ
    --project-profile B01 \਍    ⴀⴀ漀甀琀 漀甀琀⼀瘀椀爀⸀樀猀漀渀ഀ
਍⌀ 䄀倀䄀䤀 愀猀猀攀猀猀洀攀渀琀ഀ
python tools/apai_bitmap.py --vir out/vir.json --profile profiles/B01.json --out out/apai.json਍怀怀怀ഀ
਍ⴀⴀⴀഀ
਍⌀⌀ 䰀椀洀椀琀愀琀椀漀渀猀ഀ
਍ⴀ ⨀⨀吀攀砀琀ⴀ漀渀氀礀 䄀䤀 挀愀渀渀漀琀 猀攀攀 椀洀愀最攀猀⨀⨀ 搀椀爀攀挀琀氀礀⸀ 䰀椀䜀攀漀 眀漀爀欀猀 眀椀琀栀 爀攀渀搀攀爀攀爀ⴀ愀挀挀攀猀猀椀戀氀攀 挀漀渀琀攀渀琀 ⠀䠀吀䴀䰀Ⰰ 匀嘀䜀Ⰰ 瀀爀椀渀琀⼀倀䐀䘀⤀ 瘀椀愀 䌀䐀倀 愀甀琀漀洀愀琀椀漀渀Ⰰ 愀渀搀 戀椀琀洀愀瀀 椀洀愀最攀猀 瘀椀愀 搀攀琀攀爀洀椀渀椀猀琀椀挀 瀀椀砀攀氀 愀渀愀氀礀猀椀猀⸀ഀ
- **Semantic vision** (object recognition, scene understanding, aesthetic judgment) requires a separate VLM.਍ⴀ ⨀⨀伀䌀刀⨀⨀ 椀猀 琀攀砀琀 攀砀琀爀愀挀琀椀漀渀Ⰰ 渀漀琀 猀攀洀愀渀琀椀挀 甀渀搀攀爀猀琀愀渀搀椀渀最⸀ഀ
- **Profiling** is per-project; profiles must be created per book/chapter.਍ഀ
---਍ഀ
## License਍ഀ
MIT License਍ഀ
## Support਍ഀ
For issues, open an issue on GitHub or contact the AI Engineering Book Series team.
