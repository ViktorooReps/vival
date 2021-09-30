import os
from os.path import join
from enum import Enum
from typing import Optional, Dict, List, Iterable

from pydantic import BaseModel, parse_file_as


package_path = os.path.abspath(os.path.dirname(__file__))
config_path = os.path.join(package_path, 'config')


class Tag(Enum):
    DESCRIPTION = 'DESCRIPTION'
    MAIN = 'MAIN'
    FLAGS = 'FLAGS'
    TIMEOUT = 'TIMEOUT'
    COMMENT = 'COMMENT'
    STARTUP = 'STARTUP'
    CLEANUP = 'CLEANUP'
    INPUT = 'INPUT'
    CMD = 'CMD'
    OUTPUT = 'OUTPUT'


class FeatureType(Enum):
    FILE = 'File'
    TEST = 'Test'


class TagConfig(BaseModel):
    tag: Tag
    id: int
    type: FeatureType
    join_symbol: Optional[str] = '\n'
    info: Optional[str]
    default: Optional[str]


class Feature:
    """Pair tag->text representing File or Text feature of test"""

    tag_configs: Dict[Tag, TagConfig] = {config.tag: config for config in parse_file_as(List[TagConfig], join(config_path, 'tags.json'))}

    all_mods = {'mSHUFFLED', 'mENDNL', 'mENDSPACE', 'mENDNONE'}

    def __init__(self, tag: Optional[Tag], contents: Optional[Iterable[str]] = ()):
        if tag is None:
            tag = Tag.DESCRIPTION

        self.tag = tag
        self.contents = list(contents)
        self.mods = set()
        self.join_symbol = self.tag_configs[self.tag].join_symbol

        if self.is_empty() and self.default_content(self.tag) is not None:
            self.contents = [self.default_content(self.tag)]

    @classmethod
    def default_content(cls, tag: Tag):
        return cls.tag_configs[tag].default

    def apply_mod(self, *mods) -> None:
        for mod in mods:
            self.mods.add(mod)

            if mod == 'mENDNONE':
                self.join_symbol = ''
            elif mod == 'mENDNL':
                self.join_symbol = '\n'
            elif mod == 'mENDSPACE':
                self.join_symbol = ' '

    def info(self) -> Optional[str]:
        """Returns essential info for failed test"""
        return self.tag_configs[self.tag].info

    def merge_features(self, feature) -> None:
        """Pulls text from another feature.
        Appends if Test feature, replaces otherwise"""
        self.apply_mod(*feature.mods)

        if self.is_test_type():
            self.contents += feature.contents
        else:
            self.contents = feature.contents

    def is_test_type(self) -> bool:
        return self.tag_configs[self.tag].type == FeatureType.TEST

    def is_file_type(self) -> bool:
        return self.tag_configs[self.tag].type == FeatureType.FILE

    def is_empty(self) -> bool:
        return self.merged_contents() == ''

    def merged_contents(self) -> str:
        return self.join_symbol.join(self.contents)

    def __str__(self):
        """Parseable representation of feature"""
        str_repr = ''
        str_repr += self.tag.value + ' '
        for mod in self.mods:
            str_repr += mod + ' '
        str_repr += '\n'

        if self.is_empty():
            str_repr += '/{' + '}/\n\n'
        else:
            for text in self.contents:
                str_repr += '/{' + text + '}/' + self.join_symbol
            if self.join_symbol != '\n':
                str_repr += '\n\n'
            else:
                str_repr += '\n'

        return str_repr

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return self.tag_configs[self.tag].id < self.tag_configs[other.tag].id


def construct_test_features() -> List[Feature]:
    return [
        Feature(tag)
        for tag in Feature.tag_configs
        if Feature.tag_configs[tag].type == FeatureType.TEST
    ]


def construct_file_features() -> List[Feature]:
    return [
        Feature(tag)
        for tag in Feature.tag_configs
        if Feature.tag_configs[tag].type == FeatureType.FILE
    ]


class FeatureContainer:
    """Handles storing features"""
    __slots__ = (
        '_tag2feature'
    )

    def __init__(self):
        self._tag2feature: Dict[Tag, Feature] = {}

    def add_feature(self, new_feature: Feature) -> None:
        if new_feature.tag in self._tag2feature:
            self._tag2feature[new_feature.tag].merge_features(new_feature)
        else:
            self._tag2feature[new_feature.tag] = new_feature

    def get_feature(self, tag: Tag) -> Optional[Feature]:
        return self._tag2feature[tag] if tag in self._tag2feature else None

    def replace_feature(self, new_feature: Feature) -> None:
        self._tag2feature[new_feature.tag] = new_feature
