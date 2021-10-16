import unittest

from tester.features import Feature, Tag, FeatureContainer


class FeatureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.no_content = Feature(Tag.INPUT, contents=[])
        self.empty_content = Feature(Tag.INPUT, contents=[''])
        self.some_content = Feature(Tag.INPUT, contents=['', ''])
        self.desc = Feature(Tag.DESCRIPTION, contents=['desc'])

    def test_merged_contents(self):
        self.assertEqual(self.no_content.merged_contents(), '')
        self.assertEqual(self.empty_content.merged_contents(), '')
        self.assertEqual(self.desc.merged_contents(), 'desc')
        self.assertEqual(self.some_content.merged_contents(), '\n')

    def test_is_empty(self):
        self.assertTrue(self.no_content.is_empty())
        self.assertTrue(self.empty_content.is_empty())
        self.assertFalse(self.some_content.is_empty())

    def test_merge_features(self):
        tmp_test = Feature(Tag.INPUT)
        tmp_test.merge_features(self.no_content)
        self.assertEqual(self.no_content.contents, tmp_test.contents)

        tmp_test = Feature(Tag.DESCRIPTION, contents=['desc too'])
        tmp_test.merge_features(self.desc)
        self.assertEqual(tmp_test.merged_contents(), 'desc')


class FeatureContainerTest(unittest.TestCase):

    def test_no_features(self):
        fc = FeatureContainer()
        for tag in Tag:
            self.assertIsNone(fc.get_feature(tag))

    def test_feature_adding(self):
        fc = FeatureContainer()
        feature_inp = Feature(Tag.INPUT, contents=['input'])
        feature_outp = Feature(Tag.OUTPUT, contents=['output'])

        fc.add_feature(feature_inp)
        fc.add_feature(feature_outp)

        self.assertIsNotNone(fc.get_feature(Tag.INPUT))
        self.assertIsNotNone(fc.get_feature(Tag.OUTPUT))

        self.assertEqual(fc.get_feature(Tag.INPUT).merged_contents(), 'input')
        self.assertEqual(fc.get_feature(Tag.OUTPUT).merged_contents(), 'output')

    def test_feature_replacing(self):
        fc = FeatureContainer()
        feature = Feature(Tag.DESCRIPTION, contents=['v1'])
        new_feature = Feature(Tag.DESCRIPTION, contents=['v2'])

        fc.add_feature(feature)
        fc.replace_feature(feature)
        self.assertEqual(fc.get_feature(Tag.DESCRIPTION).merged_contents(), 'v1')

        fc.add_feature(new_feature)
        self.assertEqual(fc.get_feature(Tag.DESCRIPTION).merged_contents(), 'v2')

        feature_inp = Feature(Tag.INPUT, contents=['v1'])
        new_feature_inp = Feature(Tag.INPUT, contents=['v2'])

        fc.add_feature(feature_inp)
        fc.add_feature(new_feature_inp)
        self.assertEqual(fc.get_feature(Tag.INPUT).merged_contents(), 'v1\nv2')
