from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ligo-perception",
    version="1.0.0",
    author="LiGeo Perception",
    description="Text-only AI vision engine for rendered visual evidence",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gyan4it/ligo-perception",
    packages=["ligo_perception", "tools.cv_sensors"],
    package_dir={
        "ligo_perception": "ligo_perception",
        "tools.cv_sensors": "tools/cv_sensors",
    },
    py_modules=[
        "tools.cdp_runner",
        "tools.layout_check",
        "tools.a11y_check",
        "tools.print_check",
        "tools.pdf_check",
        "tools.bitmap_check",
        "tools.pixel_check",
        "tools.ocr_adapter",
        "tools.vision_adapter",
        "tools.capability_detector",
        "tools.vir_builder",
        "tools.apai_bitmap",
        "tools.profile_loader",
    ],
    install_requires=[
        "Pillow>=9.0.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "opencv": ["opencv-python>=4.5.0"],
    },
    entry_points={
        "console_scripts": [
            "ligo=ligo_perception.cli:main",
            "ligo-perception=ligo_perception.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)