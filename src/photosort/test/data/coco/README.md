# COCO Test Images

This directory contains test images for YOLO object detection testing.

## Images

1. **boats.jpg** - Marine scene with boats and people
   - Expected detections: boat, person

2. **bus.jpg** - Street scene with public transportation
   - Expected detections: bus, person, car

3. **zidane.jpg** - Sports scene with people
   - Expected detections: person, sports ball, tie

## Source

Images are from the COCO (Common Objects in Context) dataset, commonly used for testing object detection models.

## Usage

These images are used in:
- `test_007_yolo_tagger.py` - Unit tests for YOLO detection
- `test_008_yolo_integration.py` - Integration tests for add-yolo-tags command
