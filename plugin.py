import os
import math
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QHBoxLayout,
                                 QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
                                 QFileDialog, QMessageBox, QGroupBox)
from qgis.core import (QgsProject, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsGeometry, QgsPointXY,
                       QgsVectorLayer, QgsFeature, QgsField, QgsLineString)
from qgis.gui import QgisInterface

class FlightPathGeneratorPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        # Add a menu item and toolbar button
        icon_path = os.path.join(os.path.dirname(__file__), "icon.svg")
        self.icon = QIcon(icon_path)
        self.action = QAction(self.icon, "Flight Path Generator", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Plugins", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        # Remove the menu item and toolbar icon
        if self.action:
            self.iface.removePluginMenu("&Plugins", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        # Check if a polygon layer and feature are selected
        layer = self.iface.activeLayer()
        if not layer or not layer.isSpatial():
            QMessageBox.critical(self.iface.mainWindow(), "Error", "Please select a spatial vector layer.")
            return

        selected_features = layer.selectedFeatures()
        if not selected_features:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "Please select a polygon feature to generate flight paths from.")
            return

        feature = selected_features[0]
        geom = feature.geometry()
        
        # Verify geometry is polygon
        if geom.type() != 2:  # 2 corresponds to Polygon type in QGIS
            QMessageBox.critical(self.iface.mainWindow(), "Error", "Selected feature is not a polygon.")
            return

        # Show user configuration dialog
        self.dialog = QDialog(self.iface.mainWindow())
        self.dialog.setWindowTitle("Flight Path Generator")
        if hasattr(self, "icon") and self.icon:
            self.dialog.setWindowIcon(self.icon)
        self.dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(self.dialog)

        # Configuration parameters
        param_group = QGroupBox("Configuration Parameters", self.dialog)
        param_layout = QVBoxLayout(param_group)

        # Spacing
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Line Spacing (meters):"))
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(1.0, 1000.0)
        self.spin_spacing.setValue(15.0)
        spacing_layout.addWidget(self.spin_spacing)
        param_layout.addLayout(spacing_layout)

        # Overshoot
        overshoot_layout = QHBoxLayout()
        overshoot_layout.addWidget(QLabel("Overshoot (meters):"))
        self.spin_overshoot = QDoubleSpinBox()
        self.spin_overshoot.setRange(0.0, 1000.0)
        self.spin_overshoot.setValue(10.0)
        overshoot_layout.addWidget(self.spin_overshoot)
        param_layout.addLayout(overshoot_layout)

        # Buffer
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Polygon Buffer (meters):"))
        self.spin_buffer = QDoubleSpinBox()
        self.spin_buffer.setRange(-1000.0, 1000.0)
        self.spin_buffer.setValue(0.0)
        buffer_layout.addWidget(self.spin_buffer)
        param_layout.addLayout(buffer_layout)

        # Altitude
        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Altitude (meters):"))
        self.spin_alt = QDoubleSpinBox()
        self.spin_alt.setRange(1.0, 1000.0)
        self.spin_alt.setValue(80.0)
        alt_layout.addWidget(self.spin_alt)
        param_layout.addLayout(alt_layout)

        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed (m/s):"))
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 100.0)
        self.spin_speed.setValue(5.0)
        speed_layout.addWidget(self.spin_speed)
        param_layout.addLayout(speed_layout)

        layout.addWidget(param_group)

        # File Export Group
        export_group = QGroupBox("File Export", self.dialog)
        export_layout = QVBoxLayout(export_group)

        path_layout = QHBoxLayout()
        self.txt_path = QLineEdit()
        self.txt_path.setPlaceholderText("Select output directory")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.select_output_dir)
        path_layout.addWidget(self.txt_path)
        path_layout.addWidget(btn_browse)
        export_layout.addLayout(path_layout)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Filename Base:"))
        self.txt_base_name = QLineEdit()
        self.txt_base_name.setText("Flight_Path")
        name_layout.addWidget(self.txt_base_name)
        export_layout.addLayout(name_layout)

        layout.addWidget(export_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.dialog.reject)
        
        btn_generate = QPushButton("Generate")
        btn_generate.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        btn_generate.clicked.connect(lambda: self.process(geom, layer.crs()))
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_generate)
        layout.addLayout(btn_layout)

        self.dialog.exec()

    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self.dialog, "Select Output Directory", "c:/test/kml")
        if folder:
            self.txt_path.setText(folder)

    def process(self, geom: QgsGeometry, src_crs: QgsCoordinateReferenceSystem):
        spacing = self.spin_spacing.value()
        overshoot = self.spin_overshoot.value()
        buffer_dist = self.spin_buffer.value()
        alt = self.spin_alt.value()
        speed = self.spin_speed.value()
        out_dir = self.txt_path.text().strip()
        base_name = self.txt_base_name.text().strip()

        # Step 1: Create local metric Coordinate system to perform accurate geometry math in meters
        # We must transform the centroid to geographic coordinates (lat/lon) first to build the ortho projection correctly.
        wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        to_wgs84_init = QgsCoordinateTransform(src_crs, wgs84_crs, QgsProject.instance())
        geo_centroid = to_wgs84_init.transform(geom.centroid().asPoint())
        
        proj_string = f"+proj=ortho +lat_0={geo_centroid.y()} +lon_0={geo_centroid.x()} +datum=WGS84 +units=m +no_defs"
        metric_crs = QgsCoordinateReferenceSystem.fromProj4(proj_string)
        if not metric_crs.isValid():
            metric_crs = QgsCoordinateReferenceSystem()
            metric_crs.createFromProj4(proj_string)
            
        if not metric_crs.isValid():
            QMessageBox.critical(self.dialog, "Error", "Failed to create a valid metric coordinate system for flight path calculations.")
            return
        
        # Transformations
        to_metric = QgsCoordinateTransform(src_crs, metric_crs, QgsProject.instance())
        to_wgs84 = QgsCoordinateTransform(metric_crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        to_src = QgsCoordinateTransform(metric_crs, src_crs, QgsProject.instance())

        # Copy and project geometry to metric space
        metric_geom = QgsGeometry(geom)
        metric_geom.transform(to_metric)

        # Apply buffer if specified
        if buffer_dist != 0.0:
            metric_geom = metric_geom.buffer(buffer_dist, 8)

        # Bounding box of the metric polygon
        bbox = metric_geom.boundingBox()
        x_min, x_max = bbox.xMinimum(), bbox.xMaximum()
        y_min, y_max = bbox.yMinimum(), bbox.yMaximum()
        width = x_max - x_min

        # Calculate N-S flight lines
        num_lines = int(width // spacing)
        if num_lines < 1:
            num_lines = 1
            x_positions = [x_min + width / 2.0]
        else:
            margin = width - (num_lines - 1) * spacing
            x_positions = [x_min + margin / 2.0 + i * spacing for i in range(num_lines)]

        flight_lines_metric = []
        path_points_metric = []

        # Find intersections of each vertical line with the polygon boundary
        for i, x_val in enumerate(x_positions):
            # Create a vertical line passing through the whole bounding box height
            vert_line = QgsGeometry.fromPolylineXY([QgsPointXY(x_val, y_min - 100), QgsPointXY(x_val, y_max + 100)])
            intersection = vert_line.intersection(metric_geom)
            
            if intersection.isEmpty():
                continue

            # Extract points from intersection line geometry
            vertices = []
            if intersection.isMultipart():
                for part in intersection.asGeometryCollection():
                    for pt in part.asPolyline():
                        vertices.append(pt)
            else:
                vertices = intersection.asPolyline()

            if len(vertices) < 2:
                continue

            # Sort vertices by Y to find bottom and top
            vertices.sort(key=lambda pt: pt.y())
            y_bottom = vertices[0].y()
            y_top = vertices[-1].y()

            flight_lines_metric.append((QgsPointXY(x_val, y_bottom), QgsPointXY(x_val, y_top)))

            # Extended path coordinates for continuous path
            y_bottom_ext = y_bottom - overshoot
            y_top_ext = y_top + overshoot

            if i % 2 == 0:
                # South -> North
                path_points_metric.append(QgsPointXY(x_val, y_bottom_ext))
                path_points_metric.append(QgsPointXY(x_val, y_top_ext))
            else:
                # North -> South
                path_points_metric.append(QgsPointXY(x_val, y_top_ext))
                path_points_metric.append(QgsPointXY(x_val, y_bottom_ext))

        if not flight_lines_metric:
            QMessageBox.critical(self.dialog, "Error", "Could not generate flight lines. Adjust buffer/spacing.")
            return

        # Add temporary layers to QGIS Map Canvas
        self.add_layers_to_qgis(flight_lines_metric, path_points_metric, to_src, src_crs, base_name)

        # Export KML files if output folder is set
        if out_dir:
            self.export_kml_files(flight_lines_metric, path_points_metric, to_wgs84, out_dir, base_name, speed, alt)
            QMessageBox.information(self.dialog, "Success", f"Flight paths created on canvas and saved to folder: {out_dir}")
        else:
            QMessageBox.information(self.dialog, "Success", "Flight paths rendered on map canvas successfully.")

        self.dialog.accept()

    def add_layers_to_qgis(self, flight_lines, path_points, to_src, src_crs, base_name):
        # 1. Add Flight Lines Layer
        lines_layer = QgsVectorLayer(f"MultiLineString?crs={src_crs.authid()}", f"{base_name}_AFX_Lines", "memory")
        pr = lines_layer.dataProvider()
        lines_layer.startEditing()
        pr.addAttributes([QgsField("name", QVariant.String)])
        lines_layer.updateFields()

        for idx, (p1, p2) in enumerate(flight_lines):
            # Transform back to map CRS
            pt1 = to_src.transform(QgsPointXY(p1))
            pt2 = to_src.transform(QgsPointXY(p2))

            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPolylineXY([pt1, pt2]))
            f.setAttributes([f"fl{idx+1}"])
            pr.addFeature(f)
            
        lines_layer.commitChanges()
        QgsProject.instance().addMapLayer(lines_layer)

        # 2. Add Continuous Flight Path Layer
        path_layer = QgsVectorLayer(f"LineString?crs={src_crs.authid()}", f"{base_name}_DJI_Path", "memory")
        pr_path = path_layer.dataProvider()
        path_layer.startEditing()
        
        pts_transformed = []
        for pt in path_points:
            t_pt = to_src.transform(QgsPointXY(pt))
            pts_transformed.append(t_pt)

        f_path = QgsFeature()
        f_path.setGeometry(QgsGeometry.fromPolylineXY(pts_transformed))
        pr_path.addFeature(f_path)
        path_layer.commitChanges()
        QgsProject.instance().addMapLayer(path_layer)

    def export_kml_files(self, flight_lines, path_points, to_wgs84, out_dir, base_name, speed, alt):
        # Convert flight lines to WGS84 for KML export
        lines_wgs84 = []
        for p1, p2 in flight_lines:
            pt1 = to_wgs84.transform(QgsPointXY(p1))
            pt2 = to_wgs84.transform(QgsPointXY(p2))
            lines_wgs84.append((pt1, pt2))

        # Convert path to WGS84
        path_wgs84 = []
        for pt in path_points:
            t_pt = to_wgs84.transform(QgsPointXY(pt))
            path_wgs84.append(t_pt)

        # Save flight lines KML
        lines_kml_path = os.path.join(out_dir, f"{base_name}_lines.kml")
        kml_lines_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
	<name>{base_name}_lines</name>
	<Style id="yellowLine">
		<LineStyle>
			<color>ff00ffff</color>
			<width>3</width>
		</LineStyle>
	</Style>
"""
        for idx, (p1, p2) in enumerate(lines_wgs84):
            kml_lines_content += f"""	<Placemark>
		<name>fl{idx+1}</name>
		<styleUrl>#yellowLine</styleUrl>
		<LineString>
			<tessellate>1</tessellate>
			<coordinates>
				{p1.x():.15f},{p1.y():.15f},0 {p2.x():.15f},{p2.y():.15f},0
			</coordinates>
		</LineString>
	</Placemark>\n"""
        kml_lines_content += "</Document>\n</kml>"
        with open(lines_kml_path, 'w', encoding='utf-8') as f:
            f.write(kml_lines_content)

        # Save continuous flight path KML
        path_kml_path = os.path.join(out_dir, f"{base_name}_path.kml")
        coords_str = " ".join([f"{pt.x():.15f},{pt.y():.15f},{alt:.2f}" for pt in path_wgs84])
        kml_path_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:mis="www.dji.com">
<Document>
	<name>{base_name}_path</name>
	<Style id="redLine">
		<LineStyle>
			<color>ff0000ff</color>
			<width>3</width>
		</LineStyle>
	</Style>
	<Placemark>
		<name>{base_name}_path</name>
		<styleUrl>#redLine</styleUrl>
		<ExtendedData xmlns:mis="www.dji.com">
			<mis:autoFlightSpeed>{speed:.1f}</mis:autoFlightSpeed>
			<mis:altitude>{alt:.1f}</mis:altitude>
		</ExtendedData>
		<LineString>
			<tessellate>1</tessellate>
			<altitudeMode>relativeToGround</altitudeMode>
			<coordinates>
				{coords_str}
			</coordinates>
		</LineString>
	</Placemark>
</Document>
</kml>"""
        with open(path_kml_path, 'w', encoding='utf-8') as f:
            f.write(kml_path_content)
