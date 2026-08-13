import napari
from src.myopari._segmentation_widget import SegmentationWidget

if __name__ == "__main__":

    viewer = napari.Viewer()

    myopari_widget = SegmentationWidget(viewer)

    viewer.window.add_dock_widget(myopari_widget, name="myopari")

    napari.run()
