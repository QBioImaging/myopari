from setuptools import setup, find_packages

from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="myopari",
    version="0.1.5",
    description="User-Friendly AI Software for Automated Quantitative CMR Reporting on Low-Cost, Energy-Efficient Devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    license_files=["LICENSE"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Framework :: napari",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Image Processing",
    ],
    python_requires=">=3.9",
    install_requires=[
        "napari",
        "scikit-image",
        # "llama-cpp-python",
        "onnxruntime-gpu[cuda,cudnn]",
        "huggingface-hub",
        "napari-itk-io",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    entry_points={
        "napari.manifest": [
            "myopari = myopari:napari.yaml",
        ]
    },
    package_data={
        "myopari": [
            "napari.yaml",
            "Resources/*",
            "Resources/**/*",
        ]
    },
)
