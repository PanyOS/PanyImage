import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import json
import base64
import io

import PIL.ExifTags
import PIL.Image
import PIL.ImageOps

import codecs

XML_EXT = '.xml'
ENCODE_METHOD = 'utf-8'

def setSubElements(root, elements_dict):
    for name, text in elements_dict.items():
        sub = SubElement(root, name)
        if isinstance(text, str):
            sub.text = text
        elif isinstance(text, dict):           
            for name_, text_ in text.items():
                sub_ = SubElement(sub, name_)
                if isinstance(text_, str):
                    sub_.text = text_
                elif isinstance(text_, dict):
                    for name__, text__ in text_.items():
                        sub__ = SubElement(sub_, name__)
                        sub__.text = text__
    return root

def apply_exif_orientation(image):
    try:
        exif = image._getexif()
    except AttributeError:
        exif = None

    if exif is None:
        return image

    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in exif.items()
        if k in PIL.ExifTags.TAGS
    }

    orientation = exif.get('Orientation', None)

    if orientation == 1:
        # do nothing
        return image
    elif orientation == 2:
        # left-to-right mirror
        return PIL.ImageOps.mirror(image)
    elif orientation == 3:
        # rotate 180
        return image.transpose(PIL.Image.ROTATE_180)
    elif orientation == 4:
        # top-to-bottom mirror
        return PIL.ImageOps.flip(image)
    elif orientation == 5:
        # top-to-left mirror
        return PIL.ImageOps.mirror(image.transpose(PIL.Image.ROTATE_270))
    elif orientation == 6:
        # rotate 270
        return image.transpose(PIL.Image.ROTATE_270)
    elif orientation == 7:
        # top-to-right mirror
        return PIL.ImageOps.mirror(image.transpose(PIL.Image.ROTATE_90))
    elif orientation == 8:
        # rotate 90
        return image.transpose(PIL.Image.ROTATE_90)
    else:
        return image

def load_image_file(filename):
    try:
        image_pil = PIL.Image.open(filename)
    except IOError:
        print("Open Error")
        return

    # apply orientation to image according to exif
    image_pil = apply_exif_orientation(image_pil)

    with io.BytesIO() as f:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            format = 'JPEG'
        else:
            format = 'PNG'
        image_pil.save(f, format=format)
        f.seek(0)
        return f.read()

class FormatReader(object):

    @staticmethod
    def load_xml(fileName):
        assert fileName.endswith(XML_EXT), "Unsupported file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xml_tree = ElementTree.parse(fileName, parser=parser).getroot()
        shapes = []
        try:
            verified = xml_tree.attrib['verified']
        except KeyError:
            verified = False

        for object_iter in xml_tree.findall('object'):
            bnd_box = object_iter.find("bndbox")
            label = object_iter.find('name').text
            difficult = False
            if object_iter.find('difficult') is not None:
                difficult = bool(int(object_iter.find('difficult').text))
            x_min = int(float(bnd_box.find('xmin').text))
            y_min = int(float(bnd_box.find('ymin').text))
            x_max = int(float(bnd_box.find('xmax').text))
            y_max = int(float(bnd_box.find('ymax').text))
            points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
            shapes.append((label, points, None, None, difficult))
        return {"shapes": shapes, 
                "verified": verified}

    @staticmethod
    def load_json(fileName):
        with open(fileName, "r") as f:
            json_dict = json.load(f)
        return json_dict

class FormatWriter(object):

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False

class PascalVocWriter(FormatWriter):

    def prettify(self, elem):
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())

    def gen_xml(self):
        if self.filename is None or \
                self.folder_name is None or \
                self.img_size is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        elements_dict = {'folder': self.folder_name, 
                        'filename': self.filename,
                        'path': self.local_img_path,
                        'source': {'database': self.database_src},
                        'size': {'width': str(self.img_size[1]),
                                'height': str(self.img_size[0]),
                                'depth': str(self.img_size[2]) if len(self.img_size) == 3 else '1'},
                        'segmented': '0'}

        return setSubElements(top, elements_dict)

    def add_bnd_box(self, x_min, y_min, x_max, y_max, name, difficult):
        bnd_box = {'xmin': x_min, 'ymin': y_min, 'xmax': x_max, 'ymax': y_max}
        bnd_box['name'] = name
        bnd_box['difficult'] = difficult
        self.box_list.append(bnd_box)

    def setTruncatedText(self, each_object):
        if int(float(each_object['ymax'])) == int(float(self.img_size[0])) or (int(float(each_object['ymin'])) == 1):
            return "1"
        elif (int(float(each_object['xmax'])) == int(float(self.img_size[1]))) or (int(float(each_object['xmin'])) == 1):
            return "1"
        else:
            return "0"

    def append_objects(self, top):
        for each_object in self.box_list:
            elements_dict = {'object': {'name': each_object['name'],
                                        'pose': 'Unspecified',
                                        'truncated': self.setTruncatedText(each_object),
                                        'difficult': str(bool(each_object['difficult']) & 1),
                                        'bndbox': {'xmin': str(each_object['xmin']),
                                                    'ymin': str(each_object['ymin']),
                                                    'xmax': str(each_object['xmax']),
                                                    'ymax': str(each_object['ymax'])}}}
            top = setSubElements(top, elements_dict)

    def save(self, target_file=None):
        root = self.gen_xml()
        self.append_objects(root)
        out_file = None
        if target_file is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(target_file, 'w', encoding=ENCODE_METHOD)

        prettify_result = self.prettify(root)
        out_file.write(prettify_result.decode('utf8'))
        out_file.close()

class JsonWriter(FormatWriter):

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        super().__init__(folder_name, filename, img_size, database_src, local_img_path)
        self.flags = {}
        self.shape_type = "polygon"
        self.group_id = None
        self.version = "1.0.0"

    def save(self, shape_list, name):
        imageData = load_image_file(self.local_img_path)
        json_dict = {"version": self.version,
                    "flags": self.flags,
                    "shapes": shape_list,
                    "imagePath": self.filename,
                    "imageData": base64.b64encode(imageData).decode('utf-8'),
                    "imageHeight": self.img_size[0],
                    "imageWidth": self.img_size[1]}
        with open(name, 'w') as f:
            json.dump(json_dict, f, ensure_ascii=False, indent=2)