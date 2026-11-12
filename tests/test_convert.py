"""Tests for src.vision.convert_sample_dataset — VOC-to-YOLO conversion."""
import pytest
from pathlib import Path
from src.vision.convert_sample_dataset import parse_xml, voc_to_yolo, CLASS_MAP


class TestClassMapping:
    def test_d40_maps_to_pothole(self):
        assert CLASS_MAP["D40"] == 3

    def test_d20_maps_to_alligator(self):
        assert CLASS_MAP["D20"] == 2

    def test_block_crack_maps_to_alligator(self):
        assert CLASS_MAP["Block crack"] == 2

    def test_repair_not_mapped(self):
        assert "Repair" not in CLASS_MAP


class TestVocToYolo:
    def test_full_image_box(self):
        # Box covering entire image → center at (0.5, 0.5), w=1, h=1
        cx, cy, bw, bh = voc_to_yolo(0, 0, 100, 100, 100, 100)
        assert abs(cx - 0.5) < 1e-6
        assert abs(cy - 0.5) < 1e-6
        assert abs(bw - 1.0) < 1e-6
        assert abs(bh - 1.0) < 1e-6

    def test_quarter_box(self):
        cx, cy, bw, bh = voc_to_yolo(0, 0, 50, 50, 100, 100)
        assert abs(cx - 0.25) < 1e-6
        assert abs(cy - 0.25) < 1e-6
        assert abs(bw - 0.5) < 1e-6
        assert abs(bh - 0.5) < 1e-6

    def test_normalised_range(self):
        cx, cy, bw, bh = voc_to_yolo(100, 200, 300, 400, 640, 640)
        assert 0 <= cx <= 1
        assert 0 <= cy <= 1
        assert 0 <= bw <= 1
        assert 0 <= bh <= 1


class TestParseXml:
    @pytest.fixture()
    def sample_xml(self, tmp_path):
        """Create a minimal Pascal VOC XML for testing."""
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<annotation>
    <folder>images</folder>
    <filename>test_frame.jpg</filename>
    <source>
        <database>UrbanRoadAI Custom Dataset</database>
        <timestamp_ist>2026-11-05 09:00:03</timestamp_ist>
        <latitude>12.912345</latitude>
        <longitude>77.525678</longitude>
        <speed_mps>2.5</speed_mps>
        <gps_accuracy_m>3.0</gps_accuracy_m>
    </source>
    <size>
        <width>3840</width>
        <height>2160</height>
        <depth>3</depth>
    </size>
    <object>
        <name>D40</name>
        <bndbox>
            <xmin>100</xmin>
            <ymin>200</ymin>
            <xmax>300</xmax>
            <ymax>400</ymax>
        </bndbox>
    </object>
    <object>
        <name>Block crack</name>
        <bndbox>
            <xmin>500</xmin>
            <ymin>600</ymin>
            <xmax>700</xmax>
            <ymax>800</ymax>
        </bndbox>
    </object>
</annotation>"""
        xml_path = tmp_path / "test_frame.xml"
        xml_path.write_text(xml_content)
        return xml_path

    def test_parse_filename(self, sample_xml):
        result = parse_xml(sample_xml)
        assert result["filename"] == "test_frame.jpg"

    def test_parse_dimensions(self, sample_xml):
        result = parse_xml(sample_xml)
        assert result["width"] == 3840
        assert result["height"] == 2160

    def test_parse_gps(self, sample_xml):
        result = parse_xml(sample_xml)
        assert result["meta"]["latitude"] == "12.912345"
        assert result["meta"]["longitude"] == "77.525678"

    def test_parse_timestamp(self, sample_xml):
        result = parse_xml(sample_xml)
        assert result["meta"]["timestamp_ist"] == "2026-11-05 09:00:03"

    def test_parse_objects(self, sample_xml):
        result = parse_xml(sample_xml)
        assert len(result["objects"]) == 2
        assert result["objects"][0]["class_name"] == "D40"
        assert result["objects"][1]["class_name"] == "Block crack"

    def test_parse_bbox(self, sample_xml):
        result = parse_xml(sample_xml)
        obj = result["objects"][0]
        assert obj["xmin"] == 100
        assert obj["ymin"] == 200
        assert obj["xmax"] == 300
        assert obj["ymax"] == 400

