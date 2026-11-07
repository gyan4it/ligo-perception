# LiGeo Component Inventory
**Document ID:** LIGEO_COMPONENT_INVENTORY.json  
**Version:** 1.0  
**Status:** COMPLETE  
**Source:** LiGeo_CPU_First_Vision_Upgrade_Controller.md §1 (Stage 0)

## Core Engine Modules

| Module | Path | Language | Purpose | Dependencies |
|--------|------|----------|---------|-------------|
| Core Engine | tools/cv_core.py | Python | Image loading, validation, metadata, EXIF normalization, ROI helpers | PIL, numpy |
| Layer Builder | tools/vir_builder.py | Python | Visual Intermediate Representation builder | json, pathlib, datetime, sys |

## Sensors (tools/cv_sensors/)

| Sensor | File | Input | Output | Dependencies |
|--------|------|---------|----------|-------------|
| Color | color_sensor.py | Image | Palette, histogram, luminance, contrast, edges | PIL, numpy |
| Quality | quality_sensor.py | Image | Luminance, sharpness, edges, clipping, saturation | PIL, numpy |
| Edge | edge_sensor.py | Image | Canny edges, Sobel gradients, Hough lines, contours | OpenCV, numpy |
| Geometry | geometry_sensor.py | Image | Dimensions, aspect, boundary, alignment | OpenCV, numpy |
| Similarity | similarity_sensor.py | Images | Geometric similarity, similarity score | OpenCV, numpy |
| Registration | registration_sensor.py | Images | Image alignment/registration | OpenCV, numpy |
| Region | region_sensor.py | Image | Region segmentation, thresholding | OpenCV, numpy |
| Document | document_sensor.py | Image | Document geometry, page analysis | OpenCV, numpy |
| Diagram | diagram_sensor.py | Image | Diagram analysis, layout detection | OpenCV, numpy |
| Illustration | illustration_sensor.py | Image | Illustration analysis, chart detection | OpenCV, numpy |
| Similarity | similarity_sensor.py | Images | Similarity comparison, visual matching | OpenCV, numpy |
| Register | registration_sensor.py | Images | Image registration/alignment | OpenCV, numpy |
| Background | visual_regression.py | Images | Visual regression testing | OpenCV, numpy |
| Performance | benchmark.py | Images | Benchmarking framework | OpenCV, numpy |

## Input/Output Controllers
| Component | File | Input | Output |
|-----------|------|-------|---------|
| CDP Runner | tools/cdp_runner.py | Browser automation | DOM extraction |
| Layout Check | tools/layout_check.py | HTML/SVG/PDF | Structural analysis |
| Assessment | tools/a11y_check.py | Accessibility | Accessibility validation |
| Print Check | tools/print_check.py | PDF | Print layout analysis |
| PDF Check | tools/pdf_check.py | PDF | PDF structure analysis |
| Asset ID | tools/identify.py | Image | Asset identification |
| OCR Adapter | tools/ocr_adapter.py | Image | Text extraction |
| Vision Adapter | tools/vision_adapter.py | Image | Vision processing |
| Provenance | tools/provenance_tracker.py | Data | Provenance tracking |

## Output Generation
| Component | File | Input | Output |
|-----------|------|-------|---------|
| Asset Production | tools/apai_bitmap.py | Evidence | Assessment blocks |
| Image Assets | tools/image_asset_engine.py | Evidence | Production images |
| Document Generator | tools/content_assembler.py | VIR | Book chapters |
| Quality Checker | tools/qa_validator.py | VIR | Quality reports |
| Coverage Tracker | tools/coverage_tracker.py | Evidence | Coverage reports |

## Configuration
| File | Path | Purpose |
|------|------|---------|
| B01 Profile | profiles/B01.json | Book 01 configuration |
| Generic Profile | profiles/generic.json | Generic configuration |
| Asset Registry | assets/asset_registry.json | Asset registry |
| Standards Schema | specs/standards_schema.json | Standards schema |

## Test Suite
| Test File | File | Status |
|-----------|------|--------|
| Core Test | tests/test_cv_core.py | Present |
| Bitmap Test | tests/test_bitmap_check.py | Present |
| Pixel Check Test | tests/test_pixel_check.py | Present |
| OCR Test | tests/test_ocr_adapter.py | ✅ Present |
| Color Sensor Test | tests/test_color_sensor.py | ✅ Present |
| Edge Sensor Test | tests/test_edge_sensor.py | ✅ Complete |
| Quality Sensor Test | tests/test_quality_sensor.py | ✅ Complete |
| Geometry Sensor Test | tests/test_geometry_sensor.py | ✅ Complete |
| Similarity Sensor Test | tests/test_similarity_sensor.py | ✅ Complete |
| Registration Sensor Test | tests/test_registration_sensor.py | ✅ Complete |
| Region Sensor Test | tests/test_region_sensor.py | ✅ Complete |
| Document Sensor Test | tests/test_document_sensor.py | ✅ Complete |
| Diagram Sensor Test | tests/test_diagram_sensor.py | ✅ Complete |
| Illustration Sensor Test | tests/test_illustration_sensor.py | ✅ Complete |
| PDF Text Adapter Test | tests/test_pdf_text_adapter.py | ✅ Complete |
| VIR Builder Test | tests/test_vir_builder.py | ✅ Complete |
| Integration Test | tests/test_integration.py | ✅ Complete |

## Fixtures
| File | Type | Size |
|------|------|------|
| test_image.png | Test image | 7500 bytes |
| text_image.png | Test image | 7500 bytes |
| text_heavy.png | Test image | 6863 bytes |
| violations.png | Test image | 706 bytes |
| clean.png | Test image | 590 bytes |
| test_text.pdf | Test PDF | 999 bytes |
| violences.png | Violation image | 706 bytes |
| Additional fixtures | Various | Present |
