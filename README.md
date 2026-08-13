[![License MIT](https://img.shields.io/pypi/l/myopari.svg?color=green)](https://github.com/minhnhattrinh312/myopari/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/myopari.svg?color=green)](https://pypi.org/project/myopari)
[![Python Version](https://img.shields.io/pypi/pyversions/myopari.svg?color=green)](https://python.org)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/myopari)](https://napari-hub.org/plugins/myopari)

# 🫀 myopari

**myopari: An Open-Source Edge AI Framework for Automated Quantitative Cardiac MRI Analysis.**

## 💓 Introduction

myopari is a [napari](https://napari.org/) plugin for cardiac MRI segmentation and quantitative report generation. It brings ONNX-based AI inference to edge devices through an interactive interface that works with both 2D images and 3D volumes.

### ✨ Main features

- 🧠 Built-in `TIRAMISU_ACDC` and `TIRAMISU_EMIDEC` segmentation models
- 🖥️ Local, edge-friendly ONNX inference
- 🫀 Optional myocardium-only segmentation
- 📊 Per-class volume measurements and myocardium mass estimates
- 📄 Markdown report generation with optional patient information
- 🤖 Optional LLM-assisted report rewriting with `llama-cpp-python`

### 🎯 Model segmentation outputs

The output label groups for each model are defined as below:

| Model | Segmentation output | Label value(s) |
| --- | --- | --- |
| `TIRAMISU_ACDC` | Right ventricle | `1` |
| `TIRAMISU_ACDC` | Myocardium | `2` |
| `TIRAMISU_ACDC` | Left ventricle | `3` |
| `TIRAMISU_EMIDEC` | Cavity | `1` |
| `TIRAMISU_EMIDEC` | Myocardium | `2`, `3`, `4` |
| `TIRAMISU_EMIDEC` | Infarction | `3`, `4` |
| `TIRAMISU_EMIDEC` | No-reflow | `4` |

Some EMIDEC groups intentionally overlap: infarction and no-reflow are included in the broader myocardium group for quantitative reporting.

## 🚀 Usage

1. Launch napari.
2. Load a cardiac MRI image or volume.
3. Open `Plugins → myopari → myopari`.
4. Click **Select image layer** and choose the image to analyze.
5. Select the edge device and segmentation model.
6. Optionally enable **Myocardium only**.
7. Click **Segment**. The result appears as a new labels layer named `segmentation_<input_layer_name>_<count>`.

### 📝 Create a report

After segmentation:

1. Optionally click **Choose patient info files** and select `.cfg`, `.txt`, or `.md` files.
2. Optionally enable **Use LLM for report**.
3. Click **Create report**.
4. Click **Save report to .md** to export the result.

The report includes per-label volumes in mL and an estimated myocardium mass. If a logo is available in `Resources`, it is embedded in the report and copied beside the saved Markdown file.

## ⌨️ Installation Guide (Command Line)

The commands below create a dedicated Conda environment, install napari, automatically select the appropriate CPU or CUDA wheel for `llama-cpp-python`, and install myopari:

```bash
conda create -y -n myopari python=3.13
conda activate myopari
pip install "napari[all]==0.7.1"

# Check your CUDA version. If nvidia-smi is unavailable, use the CPU command.
# CPU:
pip install llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
# CUDA (replace cu124 with your CUDA wheel tag, for example cu118 or cu121):
pip install llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu132
pip install myopari

napari
```

After napari opens, select `Plugins → myopari → myopari`.

## 🧩 Installation Guide *(No Code — Highly Recommended)*

This is the easiest installation method; no terminal or programming experience is required. 🎉

1. Download and install the official napari bundled app:
   - 🪟 [Windows installer](https://github.com/napari/napari/releases/download/v0.7.1/napari-0.7.1-Windows-x86_64.exe)
   - 🐧 [Linux installer](https://github.com/napari/napari/releases/download/v0.7.1/napari-0.7.1-Linux-x86_64.sh)
   - 📘 [Official bundled-app guide](https://napari.org/0.7.1/tutorials/fundamentals/installation_bundle_conda.html)
2. Before installing myopari, install `llama-cpp-python` using the installer for your operating system:
   - 🪟 **Windows:** Download [install_llama2napari_windows.bat](https://github.com/minhnhattrinh312/myopari/releases/download/v0.1.4/install_llama2napari_windows.bat), double-click it, and follow the prompts.
   - 🐧 **Linux:** Download [install_llama2napari_linux.sh](https://github.com/minhnhattrinh312/myopari/releases/download/v0.1.4/install_llama2napari_linux.sh), run it by bash, and follow the prompts.
3. Open napari after the `llama-cpp-python` installation finishes.
4. Go to `Plugins → Install/Uninstall Plugins`.
5. Search for **myopari**.
6. Click **Install** and restart napari when installation finishes.
7. Open the plugin from `Plugins → myopari → myopari`. ✅

The plugin is also listed on the [napari hub](https://napari-hub.org/plugins/myopari).

## 🛠️ Troubleshooting

- **Segmentation runtime/provider issues:** Check whether `onnxruntime` or `onnxruntime-gpu` is installed. For GPU inference, ensure that the CUDA and driver versions match the installed ONNX Runtime build.
- **LLM report generation fails:** Install `llama-cpp-python` in napari's environment and ensure internet access is available for the first model download. Disable **Use LLM for report** to continue with standard report generation.
- **Plugin is missing after installation:** Restart napari and check `Plugins → Install/Uninstall Plugins` to confirm that myopari is installed and enabled.

## 📜 License

myopari is open-source software licensed under the [MIT License](LICENSE).
