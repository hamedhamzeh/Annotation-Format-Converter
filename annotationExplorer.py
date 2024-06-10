#%%
"""
AnnotationExplorer Class Documentation
---------------------------------------

This class is designed to explore a zip file containing annotation files for object detection tasks.
It identifies the format of the annotation files within the zip archive, supporting three common formats:
Pascal VOC XML, YOLO, and COCO JSON. The class organizes the files into separate folders based on their type and
 handles nested folders within the zip file structure, ensuring that annotation files located at any level of nesting are properly detected.

Class Usage:
    explorer = AnnotationExplorer(zip_path)
    results = explorer.explore_and_organize()
    print(f"Annotation format detected: {results['annotation_format']}")
    print(f"Number of images: {results['num_images']}")
    print(f"Number of annotation files: {results['num_annotations_files']}")

Class Methods:
    1. __init__(self, zip_path: str)
        - Initializes the AnnotationExplorer object with the path to the zip file containing annotation data.
        - Ensures that the organized directory has a unique name to avoid conflicts.
        - Initializes attributes to store the identified format, and the number of images and annotation files.

    2. _ensure_unique_organized_dir(self)
        - Ensures that the organized directory has a unique name by appending a counter if necessary.

    3. extract_zip(self)
        - Extracts the contents of the zip file to a temporary directory for further processing.

    4. organize_files_and_identify_format(self)
        - Identifies the annotation format and organizes files into separate folders.
        - Creates separate folders for annotation files based on their format:
          - 'annotations/xml' for Pascal VOC
          - 'annotations/coco' for COCO
          - 'annotations/yolo' for YOLO
          - 'images' for all image files
        - Updates the identified format and counts the number of images and annotation files.
        - Returns the identified annotation format.

    5. _move_file(self, file_path: str, destination_folder: str)
        - Moves a file to the specified destination folder, creating the folder if it does not exist.

    6. _is_pascal_voc(self, file_path: str) -> bool
        - Checks if the given file is a Pascal VOC XML annotation file.
        - Returns True if the file is in Pascal VOC XML format, False otherwise.

    7. _is_yolo(self, file_path: str) -> bool
        - Checks if the given file is a YOLO annotation file.
        - Returns True if the file is in YOLO format, False otherwise.

    8. _is_coco(self, file_path: str) -> bool
        - Checks if the given file is a COCO JSON annotation file.
        - Returns True if the file is in COCO JSON format, False otherwise.

    9. cleanup(self)
        - Cleans up the extracted files while keeping organized images and annotations folders.

    10. explore_and_organize(self)
        - Main method to extract, organize, identify format, and cleanup.
        - Returns a dictionary containing the identified annotation format, the number of images, and the number of annotation files.

Note:
    - The AnnotationExplorer class is designed to be instantiated with the path to a zip file containing annotation data.
    - It provides methods to explore the zip file, identify the annotation format, and clean up temporary files.
    - The class is robust and handles nested folders within the zip file structure.
"""

#%%
import zipfile
import os
import shutil
import json
import xml.etree.ElementTree as ET


class AnnotationExplorer:
    def __init__(self, zip_path: str):
        self.zip_path = zip_path
        # Create the folder structure and get the base directory and other paths
        self.base_dir, self.train_images_dir, self.cocos_dir = self._create_folder_structure()
        self.extract_dir = "extracted_files"
        self.identified_format = None
        self.num_images = 0
        self.num_annotations = 0

    def _create_folder_structure(self):
        """Creates a folder structure based on the name of a given zip file.

            It creates a main directory named `converted_{zip_file_name}` and initializes three
            subdirectories and three JSON files within it.

            Folder Structure:
            The function creates the following folder structure:
            converted_{zip_file_name}/
            ├── train_images/
            ├── validation_images/
            └── cocos/
                ├── train_coco.json
                ├── val_coco.json
                └── test_coco.json

            JSON Structure:
            Each JSON file is initialized with the following structure:
            {
                "info": {},
                "images": [],
                "categories": [],
                "licenses": [],
                "errors": [],
                "annotations": [],
                "labels": [],
                "classifications": [],
                "augmentation_settings": {},
                "tile_settings": {},
                "False_positive": {}
            }
            """
        dataset_name = os.path.basename(self.zip_path)
        # Create the base directory
        base_dir = f'converted_{dataset_name}'
        os.makedirs(base_dir, exist_ok=True)

        # Create the subdirectories
        train_images_dir = os.path.join(base_dir, 'train_images')
        validation_images_dir = os.path.join(base_dir, 'validation_images')
        cocos_dir = os.path.join(base_dir, 'cocos')
        os.makedirs(train_images_dir, exist_ok=True)
        os.makedirs(validation_images_dir, exist_ok=True)
        os.makedirs(cocos_dir, exist_ok=True)

        # Define the default JSON structure
        default_coco_structure = {
            "info": {},
            "images": [],
            "categories": [],
            "licenses": [],
            "errors": [],
            "annotations": [],
            "labels": [],
            "classifications": [],
            "augmentation_settings": {},
            "tile_settings": {},
            "False_positive": {}
        }

        # List of coco files to create
        coco_files = ['val_coco.json', 'test_coco.json']

        # Create the coco JSON files with the default structure
        for coco_file in coco_files:
            coco_file_path = os.path.join(cocos_dir, coco_file)
            with open(coco_file_path, 'w') as f:
                json.dump(default_coco_structure, f, indent=4)

        print(f"Folder structure and JSON files created under {base_dir}")

        return base_dir, train_images_dir, cocos_dir

    def extract_zip(self):
        """Extracts the zip file to a temporary directory."""
        os.makedirs(self.extract_dir, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.extract_dir)

    #TODO refactor format converters into one class
    #TODO go through the whole proccess
    def organize_files_and_identify_format(self):
        """
        Identifies the annotation format and organizes files into separate folders.

        Creates separate folders for annotation files based on their format:
        - 'annotations/xml' for Pascal VOC
        - 'annotations/coco' for COCO
        - 'annotations/yolo' for YOLO
        - 'images' for all image files

        Returns:
            str: The identified annotation format ('Pascal VOC', 'COCO', 'YOLO') or None if no format is recognized.
        """

        annotations_dir = os.path.join(self.base_dir, 'annotations')
        os.makedirs(annotations_dir, exist_ok=True)

        images_dir = self.train_images_dir

        for root, _, files in os.walk(self.extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    shutil.move(file_path, os.path.join(images_dir, file))
                    self.num_images += 1
                elif file.endswith('.xml'):
                    if self._is_pascal_voc(file_path):
                        self._move_file(file_path, os.path.join(annotations_dir, 'xml'))
                        self.identified_format = 'Pascal VOC'
                        self.num_annotations += 1
                elif file.endswith('.txt'):
                    if self._is_yolo(file_path):
                        self._move_file(file_path, os.path.join(annotations_dir, 'yolo'))
                        self.identified_format = 'YOLO'
                        self.num_annotations += 1
                elif file.endswith('.json'):
                    if self._is_coco(file_path):
                        self._move_file(file_path, os.path.join(annotations_dir, 'coco'))
                        self.identified_format = 'COCO'
                        self.num_annotations += 1

    def _move_file(self, file_path: str, destination_folder: str):
        """Moves a file to the specified destination folder."""
        os.makedirs(destination_folder, exist_ok=True)
        shutil.move(file_path, destination_folder)

    def _is_pascal_voc(self, file_path: str) -> bool:
        """Checks if the file is a Pascal VOC XML annotation."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            if root.tag == 'annotation' and root.find('object') is not None:
                return True
        except ET.ParseError:
            pass
        return False

    def _is_yolo(self, file_path: str) -> bool:
        """Checks if the file is a YOLO annotation."""
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) == 5 and all(part.replace('.', '', 1).isdigit() for part in parts):
                        return True
        except Exception:
            pass
        return False

    def _is_coco(self, file_path: str) -> bool:
        """Checks if the file is a COCO JSON annotation."""
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                if 'annotations' in data and 'images' in data and 'categories' in data:
                    return True
        except json.JSONDecodeError:
            pass
        return False

    def cleanup(self):
        """Cleans up the extracted files while keeping organized images and annotations folders."""
        for root, dirs, files in os.walk(self.extract_dir, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                shutil.rmtree(os.path.join(root, dir))
        if os.path.exists(self.extract_dir):
            os.rmdir(self.extract_dir)

    def explore_and_organize(self):
        """Main method to extract, organize, identify format, and cleanup."""
        self.extract_zip()
        self.organize_files_and_identify_format()
        self.cleanup()
        return {
            'dataset_name': os.path.basename(self.zip_path),
            'annotation_format': self.identified_format,
            'num_images': self.num_images,
            'num_annotations_files': self.num_annotations
        }


#%% Example usage:
explorer = AnnotationExplorer("Example Datasets/Dental_1.v4i.coco.zip")
results = explorer.explore_and_organize()
print(results)
