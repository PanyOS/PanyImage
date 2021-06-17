import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
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