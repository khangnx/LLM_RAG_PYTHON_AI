#!/bin/sh
set -e
python -c "import easyocr, cv2; print('OK', cv2.__version__)"
