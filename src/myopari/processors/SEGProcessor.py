# import torch
import onnxruntime as ort

ort.preload_dlls(directory="")

print(ort.get_available_providers())

import os

# import the functions_utils module
from .functions_utils import *

from enum import Enum


class SegModel(Enum):
    """Supported reconstruction modes."""

    TIRAMISU_ACDC = 0
    TIRAMISU_EMIDEC = 1


class EdgeDevice(Enum):
    JETSON_NANO = 0
    RASBERRY_PI = 1


class SEG_module:
    def __init__(self):
        self.model_name = SegModel.TIRAMISU_ACDC.value
        self.myo_only = False
        self.edge_device = EdgeDevice.JETSON_NANO.value

    def segment(self, volume):
        # volume have shape (H, W, D)
        if self.model_name == SegModel.TIRAMISU_ACDC.value:
            model_path = os.path.join(os.path.dirname(__file__), "../Resources/tiramisu_acdc_fp32.onnx")
            if self.edge_device == EdgeDevice.RASBERRY_PI.value:
                # self.device = torch.device("cpu")
                provider = ["CPUExecutionProvider"]
                self.model = ort.InferenceSession(model_path, providers=provider)

            else:
                # self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                provider = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                self.model = ort.InferenceSession(model_path, providers=provider)

        elif self.model_name == SegModel.TIRAMISU_EMIDEC.value:
            model_path = os.path.join(os.path.dirname(__file__), "../Resources/tiramisu_emidec_fp32.onnx")
            if self.edge_device == EdgeDevice.RASBERRY_PI.value:
                self.fb16 = False
                # self.device = torch.device("cpu")
                provider = ["CPUExecutionProvider"]
                self.model = ort.InferenceSession(model_path, providers=provider)
            else:
                provider = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                # self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                self.model = ort.InferenceSession(model_path, providers=provider)

        else:
            raise ValueError(f"Model name {self.model_name} not supported")
        # self.model.to(self.device)
        # self.model.eval()
        self.fp16 = False
        self.onnx = True
        self.device = "cpu"
        data = preprocess_data_array(volume)
        if self.model_name == SegModel.TIRAMISU_ACDC.value:
            num_class = 4
            seg_array = predict_data_model(
                data,
                self.model,
                num_classes=num_class,
                min_size_remove=800,
                fp16=self.fp16,
                device=self.device,
                onnx=self.onnx,
            ).astype(np.uint8)
            if self.myo_only:
                seg_array[seg_array != 2] = 0
            return seg_array
        elif self.model_name == SegModel.TIRAMISU_EMIDEC.value:
            num_class = 5
            seg_array = predict_data_model_emidec(
                data, self.model, fp16=self.fp16, device=self.device, onnx=self.onnx
            ).astype(np.uint8)
            if self.myo_only:
                seg_array[seg_array == 1] = 0
                seg_array[seg_array >= 2] = 2

            return seg_array
