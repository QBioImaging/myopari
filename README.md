# myopari

myopari is a napari plugin for cardiac MRI segmentation and report generation.
It provides an interactive widget to:

- select a 2D or 3D image layer,
- run ONNX-based segmentation,
- compute basic volumetric metrics,
- optionally enrich the report with an LLM rewrite,
- save a markdown report.

## Main Features

- Napari dock widget for interactive segmentation
- Built-in segmentation models:
	- `TIRAMISU_ACDC`
	- `TIRAMISU_EMIDEC`
- Works with both 2D images and 3D volumes
- Optional myocardium-only segmentation mode
- Markdown report generation with:
	- per-class volumes (mL)
	- myocardium mass estimate (g)
	- optional external patient info files (`.cfg`, `.txt`, `.md`)
- Optional LLM-based report rewriting (via `llama-cpp-python`)

## Requirements

- Python `>=3.9`
- napari
- NumPy
- scikit-image
- ONNX Runtime (`onnxruntime` for CPU or `onnxruntime-gpu` for CUDA)
- llama-cpp-python

## Installation

### Install from source (recommended)

```bash
git clone <your-repo-url>
cd myopari
pip install -e .
```

### Optional: force CPU runtime

If you do not want GPU runtime, install CPU ONNX Runtime explicitly:

```bash
pip install onnxruntime
```

### Optional: enable LLM report rewriting

```bash
pip install llama-cpp-python huggingface-hub
```

When enabled in the UI, the plugin loads a GGUF model from Hugging Face at runtime.

## Quick Start in napari

1. Launch napari.
2. Load a cardiac image (2D or 3D).
3. Open the widget:
	 - `Plugins -> myopari -> myopari`
4. In the widget:
	 - Click `Select image layer`
	 - Choose `Edge device`
	 - Choose `Segmentation model`
	 - (Optional) Enable `Myocardium only`
	 - Click `Segment`
5. A labels layer is added with a name like:
	 - `segmentation_<input_layer_name>_<count>`

## Report Workflow

After segmentation:

1. (Optional) Click `Choose patient info files` and pick `.cfg`, `.txt`, or `.md` files.
2. (Optional) Enable `Use LLM for report`.
3. Click `Create report`.
4. Click `Save report to .md` to export.

Notes:

- The report includes per-label volumes in mL and myocardium mass estimate.
- If a logo asset exists in `Resources`, it is embedded in the report and copied next to the saved markdown file.


## Troubleshooting

- Segmentation runtime/provider issues:
	- Check installed ONNX Runtime package (`onnxruntime` vs `onnxruntime-gpu`)
	- Ensure CUDA and driver versions match your `onnxruntime-gpu` build
- LLM report generation fails:
	- Install `llama-cpp-python`
	- Ensure internet access for first model download
	- Disable `Use LLM for report` to keep standard report generation

## License

MIT. See `LICENSE`.
