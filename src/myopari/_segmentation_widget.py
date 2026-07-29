# %%
import os
import shutil
import json
from ._widget import Settings, Combo_box
from .processors import SEG_module, make_volume


import time
from magicgui import magic_factory
import napari
from qtpy.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QPushButton,
    QTabWidget,
    QLabel,
    QProgressBar,
    QFileDialog,
    QPlainTextEdit,
    QMessageBox,
    QApplication,
)


from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtGui import QTextCursor
from napari.layers import Image

from napari.qt.threading import thread_worker
from time import time
from enum import Enum
import numpy as np


# this thread is used to update the progress bar
class BarThread(QThread):
    """Thread used to update a progress bar during reconstruction.

    Computes a percent completion based on:
        value, min, max → emits progressChanged(int)

    Signals:
        progressChanged (int): Percentage (0–100).

    Attributes:
        min (int): Lower bound of the progress range.
        max (int): Upper bound of the progress range.
        value (int): Current progress position.
    """

    progressChanged = Signal(int)

    def __init__(self, parent=None):
        super(BarThread, self).__init__(parent)
        self.max = 1
        self.min = 0
        self.value = 1

    def run(self):
        percent = (self.value - self.min) / (self.max - self.min) * 100
        self.progressChanged.emit(int(percent))


class SegModel(Enum):
    """Supported reconstruction modes."""

    TIRAMISU_ACDC = 0
    TIRAMISU_EMIDEC = 1


class EdgeDevice(Enum):
    JETSON_NANO = 0
    RASBERRY_PI = 1


class SegmentationWidget(QTabWidget):

    name = "Segmentator"

    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        super().__init__()
        self.llm = None
        self.segmentation_layer_name = None
        self._segmentation_counts = {}
        self.model_label_map = self._load_model_label_map()
        self.setup_ui_segmentation()

        self.bar_thread_segmentation = BarThread(self)
        self.bar_thread_segmentation.progressChanged.connect(self.progressBar_segmentation.setValue)

    def setup_ui_segmentation(self):
        def add_section(_layout, _title):
            _layout.addWidget(QLabel(_title))
            # _layout.addWidget(QSplitter(Qt.Vertical))

        # Tab 1 - Basic settings and reconstruction

        # i) add a tab widget
        self.params_widget_basic = QWidget()
        self.addTab(self.params_widget_basic, "Myopari Segmentation")

        # ii) layout
        self.segmentation_layout = QVBoxLayout()
        self.segmentation_widget = QWidget()
        # self.basic_reconstruction_layout.addWidget(QLabel("Basic reconstruction"))
        self.segmentation_layout.addWidget(self.segmentation_widget)

        self.choose_layer_widget_segmentation = choose_layer()
        self.choose_layer_widget_segmentation.call_button.visible = False
        self.add_magic_function(self.choose_layer_widget_segmentation, self.segmentation_layout)
        select_button = QPushButton("Select image layer")
        select_button.clicked.connect(self.select_layer_segmentation)
        self.segmentation_layout.addWidget(select_button)

        settings_layout = QVBoxLayout()
        add_section(settings_layout, "Settings")
        self.segmentation_layout.addLayout(settings_layout)
        # remove space between Select image layer and settings
        self.createSettingsSegmentation(settings_layout)
        self.params_widget_basic.setLayout(self.segmentation_layout)

    def createSettingsSegmentation(self, slayout):
        self.external_info_files = []

        self.edge_device = Combo_box(
            "Edge device",
            initial=EdgeDevice.JETSON_NANO.value,
            choices=EdgeDevice,
            layout=slayout,
            write_function=self.set_segmentation_processor,
        )
        self.segmentation_model = Combo_box(
            "Segmentation model",
            initial=SegModel.TIRAMISU_ACDC.value,
            choices=SegModel,
            layout=slayout,
            write_function=self.set_segmentation_processor,
        )

        self.myo_only = Settings(
            "Myocardium only", dtype=bool, initial=False, layout=slayout, write_function=self.set_segmentation_processor
        )
        self.use_llm_for_report = Settings("Use LLM for report", dtype=bool, initial=False, layout=slayout)
        # slayout.addSpacing(500)
        # add calculate segmentation button
        calculate_btn = QPushButton("Segment")
        calculate_btn.clicked.connect(self.volume_segmentation)
        slayout.addWidget(calculate_btn)
        self.progressBar_segmentation = QProgressBar()

        # add create report button
        info_file_btn = QPushButton("Choose patient info files")
        info_file_btn.clicked.connect(self.select_external_info_files)
        slayout.addWidget(info_file_btn)

        self.selected_files_label = QLabel("No external info files selected")
        slayout.addWidget(self.selected_files_label)

        report_btn = QPushButton("Create report")
        report_btn.clicked.connect(self.create_report)
        slayout.addWidget(report_btn)

        save_report_btn = QPushButton("Save report to .md")
        save_report_btn.clicked.connect(self.save_report_to_md)
        slayout.addWidget(save_report_btn)

        # Chat-style log box to show report creation progress and loaded content.
        self.report_chat_box = QPlainTextEdit()
        self.report_chat_box.setReadOnly(True)
        self.report_chat_box.setPlaceholderText("Report generation logs will appear here...")
        self.report_chat_box.setMinimumHeight(220)
        slayout.addWidget(self.report_chat_box)

    def show_segmentation(self, image_values, fullname, **kwargs):

        if "scale" in kwargs.keys():
            scale = kwargs["scale"]
        else:
            scale = [1.0] * image_values.ndim

        if "hold" in kwargs.keys() and fullname in self.viewer.layers:

            self.viewer.layers[fullname].data = image_values

        else:
            layer = self.viewer.add_labels(
                image_values,
                name=fullname,
                affine=kwargs.get("affine"),
                metadata=kwargs.get("metadata"),
                translate=kwargs.get("translate"),
                scale=scale,
            )
            return layer

    def select_layer_segmentation(self, image: Image):
        """Select input sinogram for basic reconstruction.

        Determines whether the input is 2D or 3D and initializes the Segmentation Processor.

        Args:
            image (Image): Napari image layer selected by the user.
        """
        image = self.choose_layer_widget_segmentation.image.value

        if image.data.ndim == 3 and image.data.shape[2] > 1:
            self.input_type = "3D"
            # dict to store image data
            self.image_data = {
                "name": image.name,
                "shape": image.data.shape,
                "scale": image.scale,
                "affine": image.affine,
                "metadata": image.metadata,
                "translate": image.translate,
            }
            sz, sy, sx = image.data.shape
            print(sz, sy, sx)
            if not hasattr(self, "h_segmentation"):
                self.start_segmentation_processor()
            print(f"Selected image layer: {image.name}")
        else:
            self.input_type = "2D"
            self.image_data = {
                "name": image.name,
                "shape": image.data.shape,
                "scale": image.scale,
                "affine": image.affine,
                "metadata": image.metadata,
                "translate": image.translate,
            }
            sy, sx = image.data.shape
            print(sy, sx)
            if not hasattr(self, "h_segmentation"):
                self.start_segmentation_processor()
            print(f"Selected image layer: {image.name}")

    def volume_segmentation(self):

        # self.scale_segmentation = self.viewer.layers[self.imageRaw_name].scale

        def update_segmentation_image(stack):
            image_name = self.image_data["name"]
            current_count = self._segmentation_counts.get(image_name, 0) + 1
            self._segmentation_counts[image_name] = current_count
            self.segmentation_layer_name = f"segmentation_{image_name}_{current_count}"
            self.show_segmentation(stack, fullname=self.segmentation_layer_name, **self.image_data)
            print("Segmentation completed")

        @thread_worker(
            connect={"returned": update_segmentation_image},
        )
        def _segmentation():
            print("myocardium only: ", self.h_segmentation.myo_only)
            volume = self.get_image()
            if self.input_type == "2D":
                # add a new axis to the volume to make it 3D
                volume = volume[np.newaxis, :, :]
            # tranpose the volume from (D, H, W) to (H, W, D)
            volume_transposed = volume.transpose(2, 1, 0)

            seg = self.h_segmentation.segment(volume_transposed)
            seg = seg.transpose(2, 1, 0)

            return seg

        time_start = time()
        _segmentation()
        # calculate the time taken for segmentation in seconds
        print(f"Segmentation time: {time() - time_start:.4f} seconds")

    def create_report(self):
        if hasattr(self, "report_chat_box"):
            self.report_chat_box.clear()
        self._append_report_log("Starting report creation...")

        try:
            if not hasattr(self, "image_data"):
                self._append_report_log("No input layer selected. Please select an image layer first.")
                QMessageBox.warning(self, "Missing input", "Please select an image layer first.")
                return

            if not self.segmentation_layer_name:
                self._append_report_log("No segmentation result found. Run segmentation first.")
                QMessageBox.warning(self, "Missing segmentation", "Please run segmentation before creating a report.")
                return

            if self.segmentation_layer_name not in self.viewer.layers:
                self._append_report_log(
                    f"Segmentation layer '{self.segmentation_layer_name}' not found. Run segmentation first."
                )
                QMessageBox.warning(self, "Missing segmentation", "Please run segmentation before creating a report.")
                return

            seg = self.viewer.layers[self.segmentation_layer_name].data
            source_image_layer = self.viewer.layers[self.image_data["name"]]
            seg_layer = self.viewer.layers[self.segmentation_layer_name]
            self._append_report_log(f"Using segmentation layer: {self.segmentation_layer_name}")
            self._append_report_log(f"Segmentation shape: {seg.shape}")

            voxel_spacing = self._get_voxel_spacing(source_image_layer, seg, fallback_layer=seg_layer)
            model_key = self._get_current_model_key()
            label_groups = self._get_label_groups_for_model(model_key)

            class_volumes_ml = {}
            for label_name, label_ids in label_groups.items():
                mask = np.isin(seg, label_ids)
                vol_ml = round(make_volume(mask, voxel_spacing) / 1000, 2)
                class_volumes_ml[label_name] = vol_ml

            lines = []
            lines.append("=== Myopari Segmentation Report ===")
            lines.append(f"Input image: {self.image_data['name']}")
            lines.append(f"Segmentation layer: {self.segmentation_layer_name}")
            lines.append(f"Image shape: {self.image_data['shape']}")
            lines.append(f"Segmentation shape: {tuple(seg.shape)}")
            # lines.append(f"Voxel spacing: {voxel_spacing}")
            if self.myo_only.val:
                lines.append("Myocardium only: True")
            lines.append("")
            lines.append("Segmentation information (volume in mL):")
            if class_volumes_ml:
                for class_name, class_volume in class_volumes_ml.items():
                    lines.append(f"  {class_name}: {class_volume} mL")
            else:
                lines.append("No non-background segmentation classes found.")

            myocardium_volume_ed = class_volumes_ml.get("myocardium", 0.0)
            myocardium_mass_ed = round(myocardium_volume_ed * 1.05, 2)
            lines.append(f"Myocardium mass: {myocardium_mass_ed} g")

            if self.external_info_files:
                lines.append("")
                lines.append("External patient information:")
                for filepath in self.external_info_files:
                    self._append_report_log(f"Reading external file: {filepath}")
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read().strip()
                        if not content:
                            content = "<empty file>"

                        lines.append("")
                        lines.append(f"--- File: {os.path.basename(filepath)} ---")
                        lines.append(content)
                        preview = content[:240] + ("..." if len(content) > 240 else "")
                        self._append_report_log(f"Loaded {os.path.basename(filepath)}")
                        self._append_report_log(preview)
                    except Exception as exc:
                        err_msg = f"Failed to read {filepath}: {exc}"
                        lines.append(err_msg)
                        self._append_report_log(err_msg)
            else:
                lines.append("")
                lines.append("No external patient info files were selected.")
                self._append_report_log("No external patient info files selected.")

            report_text = "\n".join(lines)
            if self.use_llm_for_report.val:
                self._append_report_log("LLM report option enabled. Preparing model...")
                self.download_llm_model()
                self._append_report_log("Generating report with LLM...")
                report_text = self._generate_llm_report(report_text)

            report_text = self._prepend_logo_to_report(report_text)

            self.latest_report = report_text
            self._append_report_log("Report created successfully.")
            self._append_report_log("----- REPORT START -----")
            self._append_report_log(report_text)
            self._append_report_log("----- REPORT END -----")
        except Exception as exc:
            self._append_report_log(f"Report creation failed: {exc}")
            QMessageBox.critical(self, "Report error", str(exc))

    def select_external_info_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select patient info files",
            "",
            "Patient Info Files (*.cfg *.txt *.md);;All Files (*)",
        )

        if not file_paths:
            self._append_report_log("File selection canceled.")
            return

        # Keep only supported extensions, even if user picks from "All Files".
        supported_ext = {".cfg", ".txt", ".md"}
        filtered_paths = [p for p in file_paths if os.path.splitext(p)[1].lower() in supported_ext]

        if not filtered_paths:
            self.external_info_files = []
            self.selected_files_label.setText("No valid files selected (.cfg, .txt, .md)")
            self._append_report_log("No valid files selected. Allowed: .cfg, .txt, .md")
            return

        self.external_info_files = filtered_paths
        self.selected_files_label.setText(f"Selected {len(filtered_paths)} file(s)")
        self._append_report_log(f"Selected {len(filtered_paths)} external info file(s).")

    def _append_report_log(self, message):
        if not hasattr(self, "report_chat_box"):
            return
        self.report_chat_box.appendPlainText(str(message))
        self.report_chat_box.verticalScrollBar().setValue(self.report_chat_box.verticalScrollBar().maximum())
        QApplication.processEvents()

    def _append_report_stream(self, text):
        if not hasattr(self, "report_chat_box"):
            return
        self.report_chat_box.moveCursor(QTextCursor.End)
        self.report_chat_box.insertPlainText(str(text))
        self.report_chat_box.verticalScrollBar().setValue(self.report_chat_box.verticalScrollBar().maximum())
        QApplication.processEvents()

    def _get_voxel_spacing(self, image_layer, seg, fallback_layer=None):
        metadata = getattr(image_layer, "metadata", None)
        if metadata is None:
            metadata = {}
        header = None

        if isinstance(metadata, dict):
            header = metadata.get("header")
            if header is None:
                # Common alternative keys depending on loader/plugin.
                header = metadata.get("nifti_header")
                if header is None:
                    header = metadata.get("image_header")

        if header is not None and hasattr(header, "get_zooms"):
            try:
                zooms = tuple(float(v) for v in header.get_zooms())
                if len(zooms) < seg.ndim:
                    zooms = zooms + (1.0,) * (seg.ndim - len(zooms))
                return zooms[: seg.ndim]
            except Exception:
                pass

        scale_source = fallback_layer if fallback_layer is not None else image_layer
        scale_values = getattr(scale_source, "scale", None)
        if scale_values is None:
            scale = ()
        else:
            scale = tuple(float(v) for v in scale_values)
        if len(scale) < seg.ndim:
            scale = scale + (1.0,) * (seg.ndim - len(scale))
        return scale[: seg.ndim]

    def _load_model_label_map(self):
        config_path = os.path.join(os.path.dirname(__file__), "Resources", "model_label_map.json")
        if not os.path.exists(config_path):
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def _get_current_model_key(self):
        try:
            return SegModel(self.segmentation_model.val).name
        except Exception:
            return ""

    def _get_label_groups_for_model(self, model_key):
        model_entry = self.model_label_map.get(model_key, {})
        label_groups = model_entry.get("label_groups", {}) if isinstance(model_entry, dict) else {}

        if isinstance(label_groups, dict) and label_groups:
            normalized = {}
            for label_name, label_ids in label_groups.items():
                if isinstance(label_ids, list):
                    ids = [int(v) for v in label_ids]
                else:
                    ids = [int(label_ids)]
                normalized[str(label_name)] = ids
            return normalized

        # Fallback behavior if config is missing or malformed.
        return {
            "right_ventricle": [1],
            "myocardium": [2],
            "left_ventricle": [3],
        }

    def _generate_llm_report(self, base_report_text):
        if self.llm is None:
            raise RuntimeError("LLM is not loaded.")

        prompt = (
            "Rewrite the provided report into a clear, concise markdown report\n\n"
            "Clinical context: The report is based on cardiac segmentation results. "
            "Input report:\n"
            f"{base_report_text}\n"
        )

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a medical reporting assistant for cardiac segmentation. "
                        "Generate a structured markdown report with sections: Summary, Patient Information,"
                        "Segmentation Information, Clinical diagnosis."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            stream = self.llm.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=0.1,
                max_tokens=900,
            )

            self._append_report_log("LLM output stream:")
            collected = []
            for chunk in stream:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    collected.append(token)
                    self._append_report_stream(token)

            self._append_report_stream("\n")
            llm_text = "".join(collected).strip()
            if not llm_text:
                self._append_report_log("LLM returned empty content, using base report.")
                return base_report_text
            return llm_text

        except TypeError:
            # Fallback for llama_cpp builds that do not accept stream with chat completion.
            response = self.llm.create_chat_completion(
                messages=[
                    messages[0],
                    messages[1],
                ],
                temperature=0.1,
                max_tokens=900,
            )
            llm_text = response["choices"][0]["message"]["content"].strip()
            if not llm_text:
                self._append_report_log("LLM returned empty content, using base report.")
                return base_report_text
            return llm_text
        except Exception as exc:
            self._append_report_log(f"LLM generation failed: {exc}. Using base report.")
            return base_report_text

    def _prepend_logo_to_report(self, report_text):
        logo_path = self._get_logo_path()
        if not os.path.exists(logo_path):
            self._append_report_log(f"Logo file not found, skipping logo embed: {logo_path}")
            return report_text

        logo_md = f"![QBI Logo]({logo_path})"
        if report_text.lstrip().startswith("![QBI Logo]"):
            return report_text

        return f"{logo_md}\n\n{report_text}"

    def _get_logo_path(self):
        return os.path.join(os.path.dirname(__file__), "Resources", "qbi_logo.png")

    def _prepare_report_for_save(self, report_text, output_file_path):
        logo_path = self._get_logo_path()
        if not os.path.exists(logo_path):
            return report_text

        output_dir = os.path.dirname(output_file_path)
        logo_filename = os.path.basename(logo_path)
        logo_target_path = os.path.join(output_dir, logo_filename)

        try:
            if os.path.abspath(logo_path) != os.path.abspath(logo_target_path):
                shutil.copy2(logo_path, logo_target_path)
                self._append_report_log(f"Copied logo next to report: {logo_target_path}")
        except Exception as exc:
            self._append_report_log(f"Failed to copy logo next to report: {exc}")
            return report_text

        return report_text.replace(f"![QBI Logo]({logo_path})", f"![QBI Logo]({logo_filename})")

    def save_report_to_md(self):
        if not hasattr(self, "latest_report") or not self.latest_report.strip():
            self._append_report_log("No report available to save. Create a report first.")
            QMessageBox.information(self, "No report", "Please create a report before saving.")
            return

        default_name = "myopari_report.md"
        if hasattr(self, "image_data") and "name" in self.image_data:
            safe_name = str(self.image_data["name"]).replace(" ", "_")
            default_name = f"myopari_report_{safe_name}.md"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save report as markdown",
            default_name,
            "Markdown Files (*.md);;All Files (*)",
        )

        if not file_path:
            self._append_report_log("Save report canceled.")
            return

        if not file_path.lower().endswith(".md"):
            file_path = file_path + ".md"

        try:
            report_to_save = self._prepare_report_for_save(self.latest_report, file_path)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_to_save)
                if not report_to_save.endswith("\n"):
                    f.write("\n")
            self._append_report_log(f"Report saved to: {file_path}")
            QMessageBox.information(self, "Report saved", f"Report saved to:\n{file_path}")
        except Exception as exc:
            self._append_report_log(f"Failed to save report: {exc}")
            QMessageBox.critical(self, "Save error", str(exc))

    def get_image(self):
        try:
            return self.viewer.layers[self.image_data["name"]].data
        except:
            raise (KeyError(r"Please select a valid image"))

    def set_segmentation_processor(self, *args):

        if hasattr(self, "h_segmentation"):

            self.h_segmentation.model_name = self.segmentation_model.val
            self.h_segmentation.myo_only = self.myo_only.val
            self.h_segmentation.edge_device = self.edge_device.val

    def stop_segmentation_processor(self):
        """Stop the Segmentation Processor instance."""
        if hasattr(self, "h_segmentation"):
            delattr(self, "h_segmentation")

    def start_segmentation_processor(self):
        """Initialize or reset the Segmentation Processor instance."""

        if hasattr(self, "h_segmentation"):
            self.stop_segmentation_processor()
            self.start_segmentation_processor()
        else:
            print("Reset")
            self.h_segmentation = SEG_module()

    def add_magic_function(self, widget, _layout):
        """Attach a magicgui widget to the layout and auto-refresh layer list.

        Args:
            widget: MagicGUI widget instance.
            _layout: Parent Qt layout.
        """
        self.viewer.layers.events.inserted.connect(widget.reset_choices)
        self.viewer.layers.events.removed.connect(widget.reset_choices)
        _layout.addWidget(widget.native)

    def download_llm_model(self):
        if self.llm is not None:
            self._append_report_log("LLM already loaded.")
            return

        REPO_ID = "unsloth/gemma-4-E2B-it-GGUF"
        FILENAME = "gemma-4-E2B-it-UD-Q4_K_XL.gguf"

        self._append_report_log("Loading llama.cpp and downloading LLM model if needed...")
        try:
            from llama_cpp import Llama
        except Exception as exc:
            raise RuntimeError("llama-cpp-python is not installed. Install it to use LLM report generation.") from exc

        self.llm = Llama.from_pretrained(
            repo_id=REPO_ID,
            # filename="gemma-4-E2B-it-UD-Q2_K_XL.gguf",
            filename=FILENAME,
            n_ctx=2048,
            n_gpu_layers=0,  # CPU only
            verbose=False,
        )
        self._append_report_log(f"LLM ready: {REPO_ID}/{FILENAME}")


@magic_factory
def choose_layer(image: Image):
    """Layer-selection helper used by magicgui."""
    pass  # TODO: substitute with a qtwidget without magic functions
